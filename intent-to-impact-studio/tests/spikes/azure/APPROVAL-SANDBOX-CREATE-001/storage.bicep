targetScope = 'resourceGroup'

@allowed(['eastus2'])
param location string

@allowed(['iticlaimsv2a4f726'])
param storageAccountName string

resource claimsStore 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  tags: {
    'architecture-component-id': 'CMP-CLAIMS-STORE'
    'operator-approval-id': 'APPROVAL-SANDBOX-CREATE-001'
    'scenario-id': 'DEMO-CASE-CLAIMS-V2'
  }
  properties: {
    accessTier: 'Hot'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    isHnsEnabled: false
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'None'
      ipRules: []
      virtualNetworkRules: []
    }
  }
}

output storageAccountId string = claimsStore.id
