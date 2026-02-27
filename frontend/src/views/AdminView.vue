<script setup lang="ts">
  import { useTopicsStore } from '@/stores/topics';
  import { useChatStore } from '@/stores/chat';
  import type { paths } from '@/types_api';
  import createClient from 'openapi-fetch';
  import { computed, onMounted, ref } from 'vue';
  import VueMarkdown from 'vue-markdown-render';
  import changeLog from '@/locales/changelog.md?raw'
  
  const client = createClient<paths>({baseUrl: import.meta.env.VITE_API_URL})
  const topicsStore = useTopicsStore()
  const chatStore = useChatStore()
  const key = ref('')
  const alert = ref('')
  const alertType = ref('success')
  const topicsEnabled = ref({} as Record<string, boolean>)

  // Configuration editing
  const configValues = ref<Record<string, unknown>>({})
  const configJson = ref('')
  const configEditMode = ref(false)
  const configLoading = ref(false)
  const configError = ref('')
  
  // Loading states
  const topicsLoading = ref(false)

  onMounted(updateStores)
  
  async function updateStores() {
    if (!topicsStore.topics) {
      await topicsStore.fetchTopics()
    }
    if (!chatStore.availableAIPurposes || chatStore.availableAIPurposes.length == 0) {
      await chatStore.fetchModels()
    }
    if(topicsStore.topics) {
      topicsEnabled.value = topicsStore.topics.reduce((acc, topic) => {
        acc[topic.endpoint] = topic.enabled
        return acc
      }, {} as Record<string, boolean>)
    }
  }

  function showAlert(message: string, type: 'success' | 'error' = 'success') {
    alert.value = message
    alertType.value = type
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      alert.value = ''
    }, 5000)
  }

  async function fetchConfig() {
    configLoading.value = true
    configError.value = ''
    
    if (!key.value) {
      configError.value = 'Please enter your admin key first'
      configLoading.value = false
      return false
    }
    
    try {
      const { data, error } = await client.GET('/admin/config', {
        params: {
          query: {
            key: key.value
          }
        }
      })
      
      if (error) {
        const errorMsg = typeof error === 'object' && error !== null ? 
          JSON.stringify(error) : 'Unknown error'
        configError.value = 'Error fetching configuration: ' + errorMsg
        return false
      }
      
      if (data && !data.success) {
        configError.value = data.error_message || 'Failed to load configuration'
        return false
      }
      
      if (data && data.config) {
        configValues.value = data.config
        configJson.value = JSON.stringify(configValues.value, null, 2)
        return true
      } else {
        configError.value = 'No configuration data received'
        return false
      }
    } catch (e: Error | unknown) {
      const errorMessage = e instanceof Error ? e.message : 'Unknown error'
      configError.value = 'Error: ' + errorMessage
      return false
    } finally {
      configLoading.value = false
    }
  }

  async function saveConfig() {
    configLoading.value = true
    configError.value = ''
    
    if (!key.value) {
      configError.value = 'Please enter your admin key first'
      configLoading.value = false
      return false
    }
    
    try {
      let updatedConfig: Record<string, unknown>
      
      if (configEditMode.value) {
        // Parse the JSON from the textarea
        try {
          updatedConfig = JSON.parse(configJson.value)
        } catch (e: Error | unknown) {
          const errorMessage = e instanceof Error ? e.message : 'Unknown error'
          configError.value = 'Invalid JSON: ' + errorMessage
          return false
        }
      } else {
        // Use the form values
        updatedConfig = { ...configValues.value }
      }
      
      const { data, error } = await client.POST('/admin/config', {
        body: {
          key: key.value,
          updates: updatedConfig
        }
      })
      
      if (error) {
        const errorMsg = typeof error === 'object' && error !== null ? 
          JSON.stringify(error) : 'Unknown error'
        configError.value = 'Error saving configuration: ' + errorMsg
        return false
      }
      
      if (!data.success) {
        configError.value = data.error_message || 'Failed to save configuration'
        return false
      }
      
      showAlert('Configuration updated successfully')
      configEditMode.value = false
      
      // Refresh the config values to show updated values
      await fetchConfig()
      return true
    } catch (e: Error | unknown) {
      const errorMessage = e instanceof Error ? e.message : 'Unknown error'
      configError.value = 'Error: ' + errorMessage
      return false
    } finally {
      configLoading.value = false
    }
  }

  async function toggleJsonEdit() {
    if (!configEditMode.value) {
      // Switching to JSON edit mode, make sure we have latest config
      if (Object.keys(configValues.value).length === 0) {
        await fetchConfig()
      }
      configJson.value = JSON.stringify(configValues.value, null, 2)
    }
    configEditMode.value = !configEditMode.value
  }

  function updateConfigValue(key: string, value: unknown) {
    configValues.value = {
      ...configValues.value,
      [key]: value
    }
  }

  async function submitTopics() {
    if (!key.value) {
      showAlert('Please enter your admin key first', 'error')
      return
    }
    
    topicsLoading.value = true
    
    try {
      const {data, error} = await client.POST('/admin/configure', {
        body: {
          key: key.value,
          enabled: topicsEnabled.value
        }
      })
      
      if (error) {
        console.error(error)
        showAlert('Error saving topics: ' + JSON.stringify(error), 'error')
      } else {
        if (!data.success) {
          showAlert(data.error_message || 'Failed to update topics', 'error')
        } else {
          showAlert('Topics updated successfully')
        }
      }
    } catch (e) {
      console.error(e)
      showAlert('Error occurred while saving topics', 'error')
    } finally {
      topicsLoading.value = false
    }
  }

  topicsStore.fetchTopics()

  const topicsSorted = computed(() => {
    const topics = topicsStore.topics
    if (!topics) return []
    return topics.sort((a, b) => {
      return b.priority - a.priority 
    })
  })

  const isBoolean = (value: unknown): value is boolean => typeof value === 'boolean'
  const isNumber = (value: unknown): value is number => typeof value === 'number'
  const isString = (value: unknown): value is string => typeof value === 'string'
</script>

<template>
  <v-container>
    <v-card class="px-4 pb-4 mb-4" :title="'Admin View'">
      <!-- Admin password at the top -->
      <v-card-text>
        <v-text-field v-model="key" 
                      hint="This password will be used for all admin operations" 
                      label="Admin Password"
                      persistent-hint
                      placeholder="Enter your admin password"
                      type="password" />
      </v-card-text>
      
      <!-- Alert for all operations -->
      <v-alert v-if="alert"
               class="mx-4 mb-4"
               closable
               :color="alertType"
               :text="alert" />
               
      <v-card-text>
        <v-expansion-panels>
          <!-- Topics Configuration Panel -->
          <v-expansion-panel :title="$t('configureTopics')">
            <v-expansion-panel-text>
              <v-form>
                <v-checkbox v-for="topic in topicsSorted"
                            :key="topic.endpoint"
                            v-model="topicsEnabled[topic.endpoint]"
                            class="mb-n4"
                            :label="topic.endpoint" />
              </v-form>
              
              <v-card-actions>
                <v-btn color="primary" 
                       :loading="topicsLoading" 
                       variant="elevated"
                       @click="submitTopics">
                  {{ $t('saveTopicsButton', 'Save Topics') }}
                </v-btn>
              </v-card-actions>
            </v-expansion-panel-text>
          </v-expansion-panel>
          
          <!-- Configuration Settings Panel -->
          <v-expansion-panel :title="$t('configurationSettings', 'Configuration Settings')">
            <v-expansion-panel-text>
              <v-card-actions class="mb-4">
                <v-btn color="primary"
                       :loading="configLoading"
                       variant="outlined"
                       @click="fetchConfig">
                  {{ $t('loadConfiguration', 'Load Configuration') }}
                </v-btn>
                <v-btn class="ml-2"
                       color="success"
                       :loading="configLoading"
                       variant="elevated"
                       @click="saveConfig">
                  {{ $t('saveConfiguration', 'Save Configuration') }}
                </v-btn>
                <v-btn class="ml-2"
                       color="info"
                       variant="outlined"
                       @click="toggleJsonEdit">
                  {{ configEditMode ? $t('formView', 'Form View') : $t('jsonEdit', 'JSON Edit') }}
                </v-btn>
              </v-card-actions>
              
              <v-alert v-if="configError"
                       class="mb-4"
                       density="compact"
                       type="error">
                {{ configError }}
              </v-alert>
              
              <!-- JSON Edit Mode -->
              <div v-if="configEditMode">
                <v-textarea v-model="configJson"
                            auto-grow
                            class="font-family-monospace"
                            :hint="$t('jsonEditHint', 'Edit JSON configuration directly')"
                            :label="$t('configurationJson', 'Configuration (JSON)')"
                            persistent-hint
                            rows="15"
                            spellcheck="false" />
              </div>
              
              <!-- Form Edit Mode -->
              <div v-else>
                <v-card v-if="Object.keys(configValues).length === 0" flat>
                  <v-card-text class="text-center">
                    {{ $t('loadConfigurationHint', 'Click "Load Configuration" to view and edit settings') }}
                  </v-card-text>
                </v-card>
                
                <div v-else class="config-form">
                  <template v-for="(value, configKey) in configValues" :key="configKey">
                    <!-- Boolean values -->
                    <v-checkbox v-if="isBoolean(value)"
                                v-model="configValues[configKey]"
                                :label="configKey"
                                @change="updateConfigValue(configKey, configValues[configKey])" />
                    
                    <!-- Number values -->
                    <v-text-field v-else-if="isNumber(value)"
                                  v-model.number="configValues[configKey]"
                                  :label="configKey"
                                  type="number"
                                  @input="updateConfigValue(configKey, Number(configValues[configKey]))" />
                    
                    <!-- String values -->
                    <v-text-field v-else-if="isString(value)"
                                  v-model="configValues[configKey]"
                                  :label="configKey"
                                  @input="updateConfigValue(configKey, configValues[configKey])" />
                    
                    <!-- Complex values (arrays, objects) -->
                    <v-textarea v-else
                                v-model="configValues[configKey]"
                                auto-grow
                                class="font-family-monospace"
                                disabled
                                :hint="$t('complexValueHint', 'Complex value - use JSON Edit mode for detailed editing')"
                                :label="configKey"
                                persistent-hint
                                rows="5"
                                spellcheck="false" />
                  </template>
                </div>
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>
    
    <v-card class="mt-4">
      <v-card-title>
        {{ $t('changelog') }}
      </v-card-title>
      <p class="px-4">
        <VueMarkdown class="chat-message" :source="changeLog" />
      </p>
    </v-card>
  </v-container>
</template>

<style scoped>
.font-family-monospace {
  font-family: monospace;
}
.config-form {
  max-width: 600px;
  margin: 0 auto;
}
</style>