targetScope = 'resourceGroup'

@description('Operator-supplied subscription ID for the intended resource-ID output; compilation does not select or validate a subscription.')
param subscriptionId string

@description('Operator-supplied Azure region. No production region is assumed.')
param location string

@minLength(3)
@maxLength(24)
@description('Operator-supplied storage account name. Compilation does not check availability.')
param storageAccountName string

// Synthetic CP-01 compile fixture, not an approved deployable architecture.
resource claimsStore 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  tags: {
    'architecture-component-id': 'CMP-CLAIMS-STORE'
    'evidence-origin': 'fixture'
  }
  properties: {
    publicNetworkAccess: 'Disabled'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'None'
    }
  }
}

output intendedStorageResourceId string = resourceId(subscriptionId, resourceGroup().name, 'Microsoft.Storage/storageAccounts', storageAccountName)
