param appName string
param location string
param tags object
param image string
param identityId string
param identityClientId string
param environmentId string
param environmentDomain string
param registryServer string
param entraClientId string
@secure()
param entraClientSecret string
param tenantId string
param operatorObjectId string
param publicDemo bool = false
param simulateModels bool = true

module app 'br/public:avm/res/app/container-app:0.23.0' = {
  name: 'studio-container'
  params: {
    name: appName
    location: location
    tags: tags
    enableTelemetry: false
    environmentResourceId: environmentId
    managedIdentities: { userAssignedResourceIds: [identityId] }
    activeRevisionsMode: 'Multiple'
    traffic: [{ latestRevision: true, weight: 100 }]
    ingressAllowInsecure: false
    ingressExternal: true
    ingressTargetPort: 8080
    ingressTransport: 'http'
    scaleSettings: { minReplicas: 1, maxReplicas: 1 }
    workloadProfileName: 'Consumption'
    secrets: [{ name: 'entra-client-secret', value: entraClientSecret }]
    registries: [{ server: registryServer, identity: identityId }]
    volumes: [{ name: 'runs', storageType: 'NfsAzureFile', storageName: 'studio-runs-nfs' }]
    initContainersTemplate: [{
      name: 'volume-owner'
      image: '${registryServer}/studio-volume-init:1'
      resources: { cpu: json('0.25'), memory: '0.5Gi' }
      volumeMounts: [{ volumeName: 'runs', mountPath: '/runs' }]
    }]
    containers: [{
      name: 'studio'
      image: image
      resources: { cpu: 1, memory: '2Gi' }
      env: [
        { name: 'STUDIO_HOSTING', value: 'aca' }
        { name: 'STUDIO_AUTH_MODE', value: publicDemo ? 'anonymous-demo' : 'entra' }
        { name: 'STUDIO_MODEL_MODE', value: simulateModels ? 'simulated' : 'live' }
        { name: 'STUDIO_PUBLIC_ORIGIN', value: 'https://${appName}.${environmentDomain}' }
        { name: 'STUDIO_ALLOWED_OBJECT_IDS', value: operatorObjectId }
        { name: 'STUDIO_TENANT_ID', value: tenantId }
        { name: 'STUDIO_MANAGED_IDENTITY_CLIENT_ID', value: identityClientId }
        { name: 'STUDIO_DATA_ROOT', value: '/app/.intent-to-impact/studio/runs' }
        { name: 'STUDIO_BICEP_PATH', value: '/usr/local/bin/bicep' }
      ]
      volumeMounts: [{ volumeName: 'runs', mountPath: '/app/.intent-to-impact/studio/runs' }]
      probes: [
        { type: 'Startup', httpGet: { path: '/healthz', port: 8080 }, periodSeconds: 5, failureThreshold: 60 }
        { type: 'Liveness', httpGet: { path: '/healthz', port: 8080 }, periodSeconds: 30, failureThreshold: 3 }
        { type: 'Readiness', httpGet: { path: '/healthz', port: 8080 }, periodSeconds: 10, failureThreshold: 3 }
      ]
    }]
    authConfig: {
      platform: { enabled: !publicDemo }
      globalValidation: {
        unauthenticatedClientAction: publicDemo ? 'AllowAnonymous' : 'RedirectToLoginPage'
        redirectToProvider: 'azureActiveDirectory'
        excludedPaths: ['/healthz']
      }
      httpSettings: { requireHttps: true }
      identityProviders: {
        azureActiveDirectory: {
          enabled: true
          registration: {
            clientId: entraClientId
            clientSecretSettingName: 'entra-client-secret'
            openIdIssuer: '${environment().authentication.loginEndpoint}${tenantId}/v2.0'
          }
          validation: {
            allowedAudiences: [entraClientId, 'api://${entraClientId}']
            defaultAuthorizationPolicy: { allowedPrincipals: { identities: [operatorObjectId] } }
          }
        }
      }
    }
  }
}
output url string = 'https://${app.outputs.fqdn}'
