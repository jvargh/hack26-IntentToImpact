param location string
param appName string
param tags object

var suffix = uniqueString(subscription().id, resourceGroup().id, appName)
var registryName = 'acr${suffix}'
var storageName = 'fs${suffix}'
module identity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'studio-identity'
  params: { name: '${appName}-identity', location: location, tags: tags, enableTelemetry: false }
}
module registry 'br/public:avm/res/container-registry/registry:0.13.1' = {
  name: 'studio-registry'
  params: {
    name: registryName
    location: location
    tags: tags
    acrSku: 'Basic'
    acrAdminUserEnabled: false
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'
    networkRuleSetDefaultAction: 'Allow'
    retentionPolicyStatus: 'disabled'
    zoneRedundancy: 'Disabled'
    azureADAuthenticationAsArmPolicyStatus: 'enabled'
    enableTelemetry: false
    roleAssignments: [{
      principalId: identity.outputs.principalId
      principalType: 'ServicePrincipal'
      roleDefinitionIdOrName: 'AcrPull'
    }]
  }
}
module network 'br/public:avm/res/network/virtual-network:0.10.2' = {
  name: 'studio-network'
  params: {
    name: '${appName}-vnet'
    location: location
    tags: tags
    enableTelemetry: false
    addressPrefixes: ['10.74.0.0/16']
    subnets: [
      {
        name: 'aca'
        addressPrefix: '10.74.0.0/23'
        delegation: 'Microsoft.App/environments'
      }
      {
        name: 'private-endpoints'
        addressPrefix: '10.74.2.0/27'
        privateEndpointNetworkPolicies: 'Disabled'
      }
    ]
  }
}
// Private NFS avoids local/shared-key authentication disabled by inherited policy.
// ACA NFS has no transport encryption; only the isolated private endpoint is reachable.
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  kind: 'FileStorage'
  sku: { name: 'Premium_LRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: false
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    publicNetworkAccess: 'Disabled'
    networkAcls: { defaultAction: 'Deny', bypass: 'None' }
    encryption: {
      keySource: 'Microsoft.Storage'
      services: { file: { enabled: true }, blob: { enabled: true } }
    }
  }
}
resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: { shareDeleteRetentionPolicy: { enabled: true, days: 7 } }
}
resource share 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: 'studio-runs'
  properties: { enabledProtocols: 'NFS', shareQuota: 100, rootSquash: 'NoRootSquash' }
}
module dns 'br/public:avm/res/network/private-dns-zone:0.8.1' = {
  name: 'studio-files-dns'
  params: {
    name: 'privatelink.file.${az.environment().suffixes.storage}'
    tags: tags
    enableTelemetry: false
    virtualNetworkLinks: [{
      name: 'studio'
      virtualNetworkResourceId: network.outputs.resourceId
      registrationEnabled: false
    }]
  }
}
module endpoint 'br/public:avm/res/network/private-endpoint:0.12.1' = {
  name: 'studio-files-endpoint'
  params: {
    name: '${appName}-nfs-pe'
    location: location
    tags: tags
    subnetResourceId: '${network.outputs.resourceId}/subnets/private-endpoints'
    enableTelemetry: false
    privateLinkServiceConnections: [{
      name: 'files'
      properties: { privateLinkServiceId: storage.id, groupIds: ['file'] }
    }]
    privateDnsZoneGroup: {
      name: 'default'
      privateDnsZoneGroupConfigs: [{ name: 'files', privateDnsZoneResourceId: dns.outputs.resourceId }]
    }
  }
}
module logs 'br/public:avm/res/operational-insights/workspace:0.16.1' = {
  name: 'studio-logs'
  params: {
    name: '${appName}-logs'
    location: location
    tags: tags
    enableTelemetry: false
    dataRetention: 30
    dailyQuotaGb: '0.1'
    forceCmkForQuery: false
  }
}
module environment 'br/public:avm/res/app/managed-environment:0.16.0' = {
  name: 'studio-environment'
  params: {
    name: '${appName}-env'
    location: location
    tags: tags
    enableTelemetry: false
    infrastructureSubnetResourceId: '${network.outputs.resourceId}/subnets/aca'
    infrastructureResourceGroupName: '${resourceGroup().name}-managed'
    publicNetworkAccess: 'Enabled'
    internal: false
    zoneRedundant: false
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
    appLogsConfiguration: { destination: 'log-analytics', logAnalyticsWorkspaceResourceId: logs.outputs.resourceId }
  }
}
resource envExisting 'Microsoft.App/managedEnvironments@2025-01-01' existing = {
  name: '${appName}-env'
}
resource mount 'Microsoft.App/managedEnvironments/storages@2025-01-01' = {
  parent: envExisting
  name: 'studio-runs-nfs'
  properties: {
    nfsAzureFile: {
      server: '${storage.name}.file.${az.environment().suffixes.storage}'
      shareName: '/${storage.name}/${share.name}'
      accessMode: 'ReadWrite'
    }
  }
  dependsOn: [environment, endpoint]
}
output registryName string = registry.outputs.name
output registryServer string = registry.outputs.loginServer
output identityId string = identity.outputs.resourceId
output identityClientId string = identity.outputs.clientId
output principalId string = identity.outputs.principalId
output environmentId string = environment.outputs.resourceId
output environmentDomain string = environment.outputs.defaultDomain
output storageAccountName string = storage.name
