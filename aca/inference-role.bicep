param principalId string
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: 'jv-eastus2-proj-resource'
}
resource inference 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, principalId, 'studio-inference')
  scope: account
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
}
