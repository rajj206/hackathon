param accountName string
param appPrincipalId string

resource openAIAccount 'Microsoft.CognitiveServices/accounts@2026-07-01' existing = {
  name: accountName
}

var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource openAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAIAccount.id, appPrincipalId, cognitiveServicesOpenAIUserRoleId)
  scope: openAIAccount
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      cognitiveServicesOpenAIUserRoleId
    )
    principalId: appPrincipalId
    principalType: 'ServicePrincipal'
  }
}
