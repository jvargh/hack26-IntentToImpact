targetScope = 'subscription'

param location string = 'eastus2'
param resourceGroupName string = 'rg-intent2impact-hack26'
param appName string = 'intent2impact-hack26'
param operatorObjectId string
param tenantId string = tenant().tenantId
param deployApp bool = false
param publicDemo bool = false
param simulateModels bool = true
param image string = ''
param entraClientId string = ''
@secure()
param entraClientSecret string = ''

var tags = {
  project: appName
  purpose: 'hackathon-studio'
  'deployed-by': operatorObjectId
}
resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}
module platform 'platform.bicep' = {
  name: '${appName}-platform'
  scope: rg
  params: {
    location: location
    appName: appName
    tags: tags
  }
}
module inference 'inference-role.bicep' = if (!simulateModels) {
  name: '${appName}-inference'
  scope: resourceGroup('az-foundry-rg')
  params: {
    principalId: platform.outputs.principalId
  }
}
module app 'app.bicep' = if (deployApp) {
  name: '${appName}-app'
  scope: rg
  params: {
    appName: appName
    location: location
    tags: tags
    image: image
    identityId: platform.outputs.identityId
    identityClientId: platform.outputs.identityClientId
    environmentId: platform.outputs.environmentId
    environmentDomain: platform.outputs.environmentDomain
    registryServer: platform.outputs.registryServer
    entraClientId: entraClientId
    entraClientSecret: entraClientSecret
    tenantId: tenantId
    operatorObjectId: operatorObjectId
    publicDemo: publicDemo
    simulateModels: simulateModels
  }
  dependsOn: [
    inference
  ]
}
output registryName string = platform.outputs.registryName
output registryServer string = platform.outputs.registryServer
output environmentDomain string = platform.outputs.environmentDomain
output appUrl string = 'https://${appName}.${platform.outputs.environmentDomain}'
output identityClientId string = platform.outputs.identityClientId
output identityPrincipalId string = platform.outputs.principalId
output storageAccountName string = platform.outputs.storageAccountName
output resourceGroup string = rg.name
