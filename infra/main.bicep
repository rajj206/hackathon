targetScope = 'subscription'

@minLength(1)
@maxLength(64)
param environmentName string

@minLength(1)
param location string

param sessionId string
param deployedBy string
param createdAt string
param deployerObjectId string

param resourceGroupName string = 'rg-experttwin-dev-4449'
param containerAppName string = 'ca-experttwin-dev-4449'
param containerAppsEnvironmentName string = 'cae-experttwin-dev-4449'
param containerRegistryName string = 'crexperttwindev4449'
param logAnalyticsName string = 'log-experttwin-dev-4449'
param applicationInsightsName string = 'appi-experttwin-dev-4449'
param keyVaultName string = 'kv-experttwin-dev-4449'

param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param existingOpenAISubscriptionId string
param existingOpenAIResourceGroupName string
param existingOpenAIAccountName string

var tags = {
  'app-onboard-skill': 'true'
  'app-onboard-session-id': sessionId
  'created-at': createdAt
  environment: environmentName
  'deployed-by': deployedBy
}

resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module logAnalytics './modules/log-analytics.bicep' = {
  name: 'log-analytics'
  scope: rg
  params: {
    location: location
    name: logAnalyticsName
    tags: tags
  }
}

module applicationInsights './modules/application-insights.bicep' = {
  name: 'application-insights'
  scope: rg
  params: {
    location: location
    name: applicationInsightsName
    tags: tags
    workspaceResourceId: logAnalytics.outputs.id
  }
}

module containerRegistry './modules/container-registry.bicep' = {
  name: 'container-registry'
  scope: rg
  params: {
    location: location
    name: containerRegistryName
    tags: tags
  }
}

module keyVault './modules/key-vault.bicep' = {
  name: 'key-vault'
  scope: rg
  params: {
    location: location
    name: keyVaultName
    tags: tags
  }
}

module containerApps './modules/container-apps.bicep' = {
  name: 'container-apps'
  scope: rg
  params: {
    location: location
    containerAppName: containerAppName
    environmentName: containerAppsEnvironmentName
    tags: tags
    workspaceName: logAnalyticsName
    workspaceCustomerId: logAnalytics.outputs.customerId
    registryLoginServer: containerRegistry.outputs.loginServer
    containerImage: containerImage
    applicationInsightsConnectionString: applicationInsights.outputs.connectionString
    azureOpenAIEndpoint: 'https://${existingOpenAIAccountName}.openai.azure.com/'
  }
}

module roleAssignments './modules/role-assignments.bicep' = {
  name: 'role-assignments'
  scope: rg
  params: {
    containerRegistryName: containerRegistryName
    keyVaultName: keyVaultName
    appPrincipalId: containerApps.outputs.principalId
    deployerObjectId: deployerObjectId
  }
  dependsOn: [
    keyVault
  ]
}

module openAIRoleAssignment './modules/openai-role-assignment.bicep' = {
  name: 'openai-role-assignment'
  scope: resourceGroup(existingOpenAISubscriptionId, existingOpenAIResourceGroupName)
  params: {
    accountName: existingOpenAIAccountName
    appPrincipalId: containerApps.outputs.principalId
  }
}

output containerAppName string = containerApps.outputs.name
output containerAppFqdn string = containerApps.outputs.fqdn
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer
output keyVaultName string = keyVault.outputs.name
