targetScope = 'subscription'

@allowed(['eastus2'])
param location string

@allowed(['rg-intent-to-impact-demo'])
param resourceGroupName string

@allowed(['iticlaimsv2a4f726'])
param storageAccountName string

resource sandbox 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: {
    'operator-approval-id': 'APPROVAL-SANDBOX-CREATE-001'
    'scenario-id': 'DEMO-CASE-CLAIMS-V2'
  }
}

module storage './storage.bicep' = {
  name: 'spk03-a001-storage'
  scope: sandbox
  params: {
    location: location
    storageAccountName: storageAccountName
  }
}

output resourceGroupId string = sandbox.id
output storageAccountId string = storage.outputs.storageAccountId
