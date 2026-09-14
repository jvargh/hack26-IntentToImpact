targetScope = 'resourceGroup'

@description('Same LOCAL-09 region for both regional resources.')
@allowed(['eastus2'])
param location string

@description('Exact empty storage account name.')
@allowed(['iticlaimsv2a4f726'])
param storageAccountName string

@description('Proposed perimeter name.')
@allowed(['nsp-iticlaims-local09'])
param perimeterName string

@description('Proposed zero-rule profile name.')
@allowed(['profile-closed'])
param profileName string

@description('Proposed Enforced association name.')
@allowed(['assoc-iticlaimsv2a4f726'])
param associationName string

resource perimeter 'Microsoft.Network/networkSecurityPerimeters@2025-01-01' = {
  name: perimeterName
  location: location
  tags: {
    'local-decision-id': 'LOCAL-09'
  }
  properties: {}
}

resource profile 'Microsoft.Network/networkSecurityPerimeters/profiles@2025-01-01' = {
  parent: perimeter
  name: profileName
  properties: {}
}

// SecuredByPerimeter starts locked down before association; never stage Enabled.
resource claimsStore 'Microsoft.Storage/storageAccounts@2025-06-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  tags: {
    'local-decision-id': 'LOCAL-09'
    'architecture-component-id': 'CMP-CLAIMS-STORE'
  }
  properties: {
    accessTier: 'Hot'
    publicNetworkAccess: 'SecuredByPerimeter'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    isHnsEnabled: false
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'None'
      ipRules: []
      virtualNetworkRules: []
    }
  }
  dependsOn: [
    profile
  ]
}

resource association 'Microsoft.Network/networkSecurityPerimeters/resourceAssociations@2025-01-01' = {
  parent: perimeter
  name: associationName
  properties: {
    accessMode: 'Enforced'
    privateLinkResource: {
      id: claimsStore.id
    }
    profile: {
      id: profile.id
    }
  }
}

output storageAccountId string = claimsStore.id
output perimeterId string = perimeter.id
output profileId string = profile.id
output associationId string = association.id
