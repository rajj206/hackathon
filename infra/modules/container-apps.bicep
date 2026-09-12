param location string
param containerAppName string
param environmentName string
param tags object
param workspaceName string
param workspaceCustomerId string
param registryLoginServer string
param applicationInsightsConnectionString string
param azureOpenAIEndpoint string
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

var placeholderImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
var isPlaceholder = containerImage == placeholderImage
var appPort = 8000
var effectivePort = isPlaceholder ? 80 : appPort

resource workspace 'Microsoft.OperationalInsights/workspaces@2026-03-01' existing = {
  name: workspaceName
}

resource environment 'Microsoft.App/managedEnvironments@2026-01-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspaceCustomerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
  }
}

resource containerApp 'Microsoft.App/containerApps@2026-01-01' = {
  name: containerAppName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      maxInactiveRevisions: 2
      ingress: {
        external: true
        allowInsecure: false
        targetPort: effectivePort
        transport: 'auto'
      }
      registries: isPlaceholder
        ? []
        : [
            {
              server: registryLoginServer
              identity: 'system'
            }
          ]
      secrets: []
    }
    template: {
      containers: [
        {
          name: 'experttwin'
          image: containerImage
          env: [
            {
              name: 'DATA_DIR'
              value: '/data'
            }
            {
              name: 'MAX_UPLOAD_MB'
              value: '25'
            }
            {
              name: 'EXTRACTOR_PROVIDER'
              value: 'azure-openai'
            }
            {
              name: 'CHAT_PROVIDER'
              value: 'azure-openai'
            }
            {
              name: 'WAR_ROOM_PROVIDER'
              value: 'azure-openai'
            }
            {
              name: 'TRANSCRIPTION_PROVIDER'
              value: 'local'
            }
            {
              name: 'SEED_ROLE_SIMULATIONS'
              value: 'true'
            }
            {
              name: 'ROLE_SIMULATIONS_CORPUS_DIR'
              value: './demo-data/role-simulations/northstar-mixed'
            }
            {
              name: 'WAR_ROOM_PROMPT_BUDGET'
              value: '24000'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAIEndpoint
            }
            {
              name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
              value: 'gpt-5.6-sol'
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: '2025-04-01-preview'
            }
            {
              name: 'AZURE_SPEECH_LANGUAGE'
              value: 'en-US'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: applicationInsightsConnectionString
            }
          ]
          resources: {
            cpu: '0.5'
            memory: '1Gi'
          }
          probes: isPlaceholder
            ? []
            : [
                {
                  type: 'Liveness'
                  httpGet: {
                    path: '/health'
                    port: appPort
                    scheme: 'HTTP'
                  }
                  initialDelaySeconds: 20
                  periodSeconds: 30
                  timeoutSeconds: 5
                  failureThreshold: 3
                }
                {
                  type: 'Readiness'
                  httpGet: {
                    path: '/health'
                    port: appPort
                    scheme: 'HTTP'
                  }
                  initialDelaySeconds: 5
                  periodSeconds: 10
                  timeoutSeconds: 5
                  failureThreshold: 6
                }
              ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

output name string = containerApp.name
output fqdn string = containerApp.properties.configuration.ingress.fqdn
output principalId string = containerApp.identity.principalId
