targetScope = 'subscription'

@description('LOCAL-09 target region; deployment still requires final confirmation.')
@allowed(['eastus2'])
param location string

@description('New resource group only. An existing group must not be adopted.')
@allowed(['rg-intent-to-impact-demo'])
param resourceGroupName string

@description('Exact account name selected by the operator; availability must be rechecked.')
@allowed(['iticlaimsv2a4f726'])
param storageAccountName string

@description('Proposed NSP name, included in the final confirmation scope.')
@allowed(['nsp-iticlaims-local09'])
param perimeterName string

@description('Proposed empty profile name, with no external access rules.')
@allowed(['profile-closed'])
param profileName string

@description('Proposed storage association name; Enforced only.')
@allowed(['assoc-iticlaimsv2a4f726'])
param associationName string

resource sandbox 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: {
    'local-decision-id': 'LOCAL-09'
  }
}

module topology './modules/nsp-storage.bicep' = {
  name: 'local09-sandbox'
  scope: sandbox
  params: {
    location: location
    storageAccountName: storageAccountName
    perimeterName: perimeterName
    profileName: profileName
    associationName: associationName
  }
}

output resourceGroupId string = sandbox.id
output storageAccountId string = topology.outputs.storageAccountId
output perimeterId string = topology.outputs.perimeterId
output profileId string = topology.outputs.profileId
output associationId string = topology.outputs.associationId
