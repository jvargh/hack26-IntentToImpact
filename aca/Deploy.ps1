[CmdletBinding()]
param(
    [string] $SubscriptionId,
    [string] $ResourceGroupName = 'rg-intent2impact-hack26',
    [string] $Location = 'eastus2',
    [string] $AppName = 'intent2impact-hack26',
    [string] $Image,
    [switch] $Provision,
    [switch] $ApproveRestart,
    [switch] $PublicDemo,
    [switch] $LiveModels
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$local = Join-Path $PSScriptRoot '.local'
New-Item -ItemType Directory -Path $local -Force | Out-Null

function Invoke-AzJson {
    param([string[]] $Arguments)
    $output = & az @Arguments --only-show-errors -o json
    if ($LASTEXITCODE -ne 0) { throw "Azure CLI failed: $($Arguments[0..([Math]::Min(2,$Arguments.Count-1))] -join ' ')" }
    if ($output) { $output | ConvertFrom-Json }
}
function Save-PrivateJson {
    param([string] $Path, $Value)
    # Generated operator-only runtime state. Never echo secrets or pass them in
    # process arguments; the entire .local directory is excluded from Git/images.
    [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 50), [Text.UTF8Encoding]::new($false))
}
$account = Invoke-AzJson @('account','show')
if (-not $SubscriptionId) { $SubscriptionId = $account.id }
if ($SubscriptionId -ne $account.id) { throw 'Select the intended default subscription with Azure CLI before running this script.' }
if ($SubscriptionId -ne '463a82d4-1896-4332-aeeb-618ee5a5aa93') {
    throw 'The current Foundry account is pinned to the approved demo subscription; review aca/inference-role.bicep before deploying to another subscription.'
}
$operator = Invoke-AzJson @('ad','signed-in-user','show')
$statePath = Join-Path $local 'deployment-state.json'
$state = if (Test-Path -LiteralPath $statePath) { Get-Content $statePath -Raw | ConvertFrom-Json -AsHashtable } else { @{} }
if ($state.subscriptionId -and ($state.subscriptionId -ne $SubscriptionId -or $state.appName -ne $AppName -or $state.resourceGroup -ne $ResourceGroupName)) {
    throw 'Existing local state belongs to another deployment. Use its original target; do not overwrite credentials.'
}
$state.subscriptionId = $SubscriptionId
$state.tenantId = $account.tenantId
$state.operatorObjectId = $operator.id
$state.appName = $AppName
$state.resourceGroup = $ResourceGroupName
$state.location = $Location
Save-PrivateJson $statePath $state
$parameters = @{
    '$schema' = 'https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#'
    contentVersion = '1.0.0.0'
    parameters = @{
        location = @{value=$Location}
        resourceGroupName = @{value=$ResourceGroupName}
        appName = @{value=$AppName}
        operatorObjectId = @{value=$operator.id}
        tenantId = @{value=$account.tenantId}
        publicDemo = @{value=[bool]$PublicDemo}
        simulateModels = @{value= -not [bool]$LiveModels}
    }
}
$parameterPath = Join-Path $local 'deployment.parameters.json'
Save-PrivateJson $parameterPath $parameters
$template = Join-Path $PSScriptRoot 'main.bicep'
Write-Output "Subscription: $($account.name) ($SubscriptionId)"
Write-Output "Resource group: $ResourceGroupName / $Location"
Write-Output "Container app: $AppName"
if (-not $Provision) {
    & az deployment sub what-if --subscription $SubscriptionId --location $Location --name "$AppName-preview" --template-file $template --parameters "@$parameterPath" --no-pretty-print --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw 'What-if failed; nothing was provisioned.' }
    Write-Output 'Preview only. Rerun with -Provision after approving the resource/cost plan.'
    return
}
Write-Warning 'Provisioning billable ACA, registry, private file storage/networking and log resources. Creates Entra sign-in registration and scoped runtime identity grants. No local histories are uploaded.'
$bootstrap = Invoke-AzJson @('deployment','sub','create','--subscription',$SubscriptionId,'--location',$Location,
    '--name',"$AppName-platform",'--template-file',$template,'--parameters',"@$parameterPath")
if ($bootstrap.properties.provisioningState -ne 'Succeeded') { throw 'Platform deployment did not succeed.' }
$outputs = $bootstrap.properties.outputs
$state.registryName = $outputs.registryName.value
$state.registryServer = $outputs.registryServer.value
$state.url = $outputs.appUrl.value
$state.identityClientId = $outputs.identityClientId.value
$state.identityPrincipalId = $outputs.identityPrincipalId.value
Save-PrivateJson $statePath $state

if (-not $state.entraApplicationId) {
    $existing = @(Invoke-AzJson @('ad','app','list','--display-name',$AppName))
    if ($existing.Count) { throw 'An Entra application with this name already exists but is not in this deployment state. Inspect it; no application was overwritten.' }
    $registration = Invoke-AzJson @('ad','app','create','--display-name',$AppName,'--sign-in-audience','AzureADMyOrg',
        '--web-redirect-uris',"$($state.url)/.auth/login/aad/callback",'--enable-id-token-issuance','true')
    $state.entraApplicationId = $registration.appId
    $state.entraObjectId = $registration.id
    Save-PrivateJson $statePath $state
}
Invoke-AzJson @('ad','app','update','--id',$state.entraApplicationId,'--enable-id-token-issuance','true',
    '--web-redirect-uris',"$($state.url)/.auth/login/aad/callback") | Out-Null
if (-not $state.delegatedScopeId) {
    $state.delegatedScopeId = [guid]::NewGuid().ToString()
    Save-PrivateJson $statePath $state
}
$authManifest = @{
    identifierUris = @("api://$($state.entraApplicationId)")
    api = @{
        requestedAccessTokenVersion = 2
        oauth2PermissionScopes = @(@{
            id = $state.delegatedScopeId
            value = 'access_as_user'
            type = 'Admin'
            isEnabled = $true
            adminConsentDisplayName = 'Access the protected Intent to Impact studio'
            adminConsentDescription = 'Use the studio as the signed-in authorized operator.'
        })
        preAuthorizedApplications = @(@{
            appId = '04b07795-8ddb-461a-bbee-02f9e1bf7b46'
            delegatedPermissionIds = @($state.delegatedScopeId)
        })
    }
}
$authManifestPath = Join-Path $local 'auth-manifest.json'
$preauthorization = $authManifest.api.preAuthorizedApplications
$authManifest.api.Remove('preAuthorizedApplications')
Save-PrivateJson $authManifestPath $authManifest
Invoke-AzJson @('rest','--method','PATCH','--url',"https://graph.microsoft.com/v1.0/applications/$($state.entraObjectId)",
    '--headers','Content-Type=application/json','--body',"@$authManifestPath") | Out-Null
$authManifest.api.preAuthorizedApplications = $preauthorization
Save-PrivateJson $authManifestPath $authManifest
Invoke-AzJson @('rest','--method','PATCH','--url',"https://graph.microsoft.com/v1.0/applications/$($state.entraObjectId)",
    '--headers','Content-Type=application/json','--body',"@$authManifestPath") | Out-Null
if (-not $state.entraServicePrincipalId) {
    $principal = Invoke-AzJson @('ad','sp','create','--id',$state.entraApplicationId)
    $state.entraServicePrincipalId = $principal.id
    Save-PrivateJson $statePath $state
}
$secretPath = Join-Path $local 'entra-secret.json'
if (-not (Test-Path -LiteralPath $secretPath)) {
    $credential = Invoke-AzJson @('ad','app','credential','reset','--id',$state.entraApplicationId,'--append',
        '--display-name',"$AppName-easyauth",'--end-date',([DateTime]::UtcNow.AddDays(90).ToString('yyyy-MM-dd')))
    Save-PrivateJson $secretPath @{secret=$credential.password;expires=([DateTime]::UtcNow.AddDays(90).ToString('o'))}
}
$credential = Get-Content $secretPath -Raw | ConvertFrom-Json
if ([DateTime]::Parse($credential.expires) -le [DateTime]::UtcNow) { throw 'Entra sign-in credential expired; rotate it explicitly before deployment.' }

if ($Image) {
    if (-not $Image.StartsWith("$($state.registryServer)/$AppName`:", [StringComparison]::Ordinal)) {
        throw 'A resumed image must be an explicit tag in this deployment registry and repository.'
    }
    $image = $Image
} else {
    $tag = [DateTime]::UtcNow.ToString('yyyyMMddHHmmss')
    $image = "$($state.registryServer)/$AppName`:$tag"
}

Push-Location $root
try {
    if (-not $Image) {
        & docker build --platform linux/amd64 --file .\aca\Dockerfile --tag $image .
        if ($LASTEXITCODE -ne 0) { throw 'Container image build failed.' }
    }
    $login = Start-Job -ScriptBlock {
        param($registry, $subscription)
        & az acr login --name $registry --subscription $subscription --only-show-errors
        if ($LASTEXITCODE -ne 0) { throw 'ACR login failed.' }
    } -ArgumentList $state.registryName, $SubscriptionId
    try {
        if (-not (Wait-Job $login -Timeout 90)) { throw 'ACR login timed out. No retry or credential bypass was attempted; use -Image only after publishing the image successfully.' }
        Receive-Job $login -ErrorAction Stop
        if ($login.State -ne 'Completed') { throw 'ACR login failed.' }
    } finally { Stop-Job $login; Remove-Job $login }
    if (-not $Image) {
        & docker push $image
        if ($LASTEXITCODE -ne 0) { throw 'Image push failed.' }
    }
    $initImage = "$($state.registryServer)/studio-volume-init:1"
    & docker build --platform linux/amd64 --file .\aca\Volume.Dockerfile --tag $initImage .
    if ($LASTEXITCODE -ne 0) { throw 'Volume ownership image build failed.' }
    & docker push $initImage
    if ($LASTEXITCODE -ne 0) { throw 'Volume ownership image push failed.' }
} finally { Pop-Location }
$state.image = $image
$state.publicDemo = [bool]$PublicDemo
$state.modelMode = if ($LiveModels) { 'live' } else { 'simulated' }
Save-PrivateJson $statePath $state
$parameters.parameters.deployApp = @{value=$true}
$parameters.parameters.image = @{value=$image}
$parameters.parameters.entraClientId = @{value=$state.entraApplicationId}
$parameters.parameters.entraClientSecret = @{value=$credential.secret}
Save-PrivateJson $parameterPath $parameters

$apps = @(Invoke-AzJson @('containerapp','list','--resource-group',$ResourceGroupName,'--subscription',$SubscriptionId))
if ($apps | Where-Object name -EQ $AppName) {
    if (-not $ApproveRestart) { throw 'An existing app must be stopped to avoid overlapping file-store writers. Finish active jobs and rerun with -ApproveRestart.' }
    Invoke-AzJson @('containerapp','revision','set-mode','--name',$AppName,'--resource-group',$ResourceGroupName,'--mode','multiple') | Out-Null
    $revisions = @(Invoke-AzJson @('containerapp','revision','list','--name',$AppName,'--resource-group',$ResourceGroupName))
    foreach ($revision in $revisions | Where-Object {$_.properties.active}) {
        Invoke-AzJson @('containerapp','revision','deactivate','--revision',$revision.name,'--resource-group',$ResourceGroupName) | Out-Null
    }
    Start-Sleep -Seconds 15
}
$deployment = Invoke-AzJson @('deployment','sub','create','--subscription',$SubscriptionId,'--location',$Location,
    '--name',"$AppName-release",'--template-file',$template,'--parameters',"@$parameterPath")
if ($deployment.properties.provisioningState -ne 'Succeeded') { throw 'Application deployment did not succeed.' }
$state.provisioningState = 'Succeeded'
$state.completedUtc = [DateTime]::UtcNow.ToString('o')
Save-PrivateJson $statePath $state
Write-Output "Deployed infrastructure and image: $($state.url)"
Write-Output 'Verify sign-in, real generation/review, package compilation and history retention before declaring functional parity.'
