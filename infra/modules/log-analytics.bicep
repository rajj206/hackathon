param location string
param name string
param tags object

resource workspace 'Microsoft.OperationalInsights/workspaces@2026-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

output id string = workspace.id
output customerId string = workspace.properties.customerId
