<script setup lang="ts">
  import {computed, onMounted, ref} from 'vue'
  import VueMarkdown from 'vue-markdown-render'
  import {VueDraggable} from 'vue-draggable-plus'
  import createClient from 'openapi-fetch'

  import {useTopicsStore} from '@/stores/topics'
  import {useChatStore} from '@/stores/chat'

  import changeLog from '@/locales/changelog.md?raw'

  import type {paths, components} from '@/types_api'

  const topicsStore = useTopicsStore()
  const chatStore = useChatStore()

  const dbInfo = ref('')
  const dbConnected = ref(false)
  const key = ref('')
  const alert = ref('')
  const alertType = ref('success')
  const topicsEnabled = ref({} as Record<string, boolean>)

  // ScaDS bots management
  const scadsBotsInfo = ref('')
  const scadsBotsLoading = ref(false)

  // Configuration editing
  const configValues = ref<Record<string, unknown>>({})
  const purposes = ref<Record<string, components["schemas"]["PurposeDB"]>>({})
  const configJson = ref('')
  const configEditMode = ref(false)
  const configLoading = ref(false)
  const configError = ref('')
  const editingModelName = ref('')
  const editing = ref('')

  // Loading states
  const topicsLoading = ref(false)

  const client = createClient<paths>({baseUrl: import.meta.env.VITE_API_URL})
  const isBoolean = (value: unknown): value is boolean => typeof value === 'boolean'
  const isNumber = (value: unknown): value is number => typeof value === 'number'
  const isString = (value: unknown): value is string => typeof value === 'string'

  topicsStore.fetchTopics()

  onMounted(updateStores)

  const topicsSorted = computed(() => {
    const topics = topicsStore.topics
    if (!topics) return []
    return topics.sort((a, b) => {
      return b.priority - a.priority
    })
  })

  async function updateStores() {
    if (!topicsStore.topics) {
      await topicsStore.fetchTopics()
    }
    if (!chatStore.availableAIPurposes || chatStore.availableAIPurposes.length == 0) {
      await chatStore.fetchModels()
    }
    if (topicsStore.topics) {
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
      const {data, error} = await client.GET('/admin/config', {
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
        purposes.value = data.purposes || {}
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
        updatedConfig = {...configValues.value}
      }

      updatedConfig["AI_MODELS"] = {
        "purposes": Object.values(purposes.value)
      }

      const {data, error} = await client.POST('/admin/config', {
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

  async function addModelToPurpose(purpose: components["schemas"]["PurposeDB"]) {
    purpose.models.push('enter-model-id-here')
  }

  async function removeModelFromPurpose(purpose: components["schemas"]["PurposeDB"], index: number) {
    purpose.models.splice(index, 1)
  }

  async function editModelName(purpose: components["schemas"]["PurposeDB"], index: number, newName: string) {
    purpose.models[index] = newName
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

  async function connectDB() {
    try {
      const {data, error} = await client.GET('/dev/db/connect')

      if (error || !data.success) {
        showAlert('Error connecting to DB: ' + JSON.stringify(error), 'error')
      } else {
        dbConnected.value = true
        dbInfo.value += data.message + '\n'
        if (data.data)
          dbInfo.value += 'Database Info: ' + JSON.stringify(data.data) + '\n'
      }
    } catch (e) {
      console.error(e)
      showAlert('Error occurred while connecting to DB', 'error')
    }
  }

  async function dropSchema() {
    try {
      const {data, error} = await client.GET('/dev/db/schema/drop')

      if (error || !data.success) {
        showAlert('Error dropping schema: ' + JSON.stringify(error), 'error')
      } else {
        dbInfo.value += data.message + '\n'
      }
    } catch (e) {
      console.error(e)
      showAlert('Error occurred while dropping schema', 'error')
    }
  }

  async function createSchema() {
    try {
      const {data, error} = await client.GET('/dev/db/schema/create')

      if (error || !data.success) {
        showAlert('Error creating schema: ' + JSON.stringify(error), 'error')
      } else {
        dbInfo.value += data.message + '\n'
      }
    } catch (e) {
      console.error(e)
      showAlert('Error occurred while creating schema', 'error')
    }
  }

  async function loadSchema() {
    try {
      const {data, error} = await client.GET('/dev/db/schema/load')

      if (error || !data.success) {
        showAlert('Error loading schema: ' + JSON.stringify(error), 'error')
      } else {
        dbInfo.value += data.message + '\n'
      }
    } catch (e) {
      console.error(e)
      showAlert('Error occurred while loading schema', 'error')
    }
  }

  async function loadData() {
    try {
      const {data, error} = await client.GET('/dev/db/data/load')

      if (error || !data.success) {
        showAlert('Error loading data: ' + JSON.stringify(error), 'error')
      } else {
        dbInfo.value += data.message + '\n'
      }
    } catch (e) {
      console.error(e)
      showAlert('Error occurred while loading data', 'error')
    }
  }

  async function validateSchema() {
    try {
      const {data, error} = await client.GET('/dev/db/schema/valid')

      if (error || !data.success) {
        showAlert('Error validating schema: ' + JSON.stringify(error), 'error')
      } else {
        dbInfo.value += data.message + '\n'
      }
    } catch (e) {
      console.error(e)
      showAlert('Error occurred while validating schema', 'error')
    }
  }

  async function refreshScadsBots() {
    if (!key.value) {
      showAlert('Please enter your admin key first', 'error')
      return
    }

    scadsBotsLoading.value = true
    scadsBotsInfo.value = ''

    try {
      const {data, error} = await client.POST('/admin/refresh-scads-bots', {
        body: {
          key: key.value
        }
      })

      if (error) {
        console.error(error)
        showAlert('Error refreshing ScaDS bots: ' + JSON.stringify(error), 'error')
      } else {
        if (!data.success) {
          showAlert(data.error_message || 'Failed to refresh ScaDS assistants', 'error')
        } else {
          const added = data.bots_added || []
          const removed = data.bots_removed || []
          const total = data.total_bots || 0
          let info = `Total assistants: ${total}`
          if (added.length > 0) {
            info += `\nAdded: ${added.join(', ')}`
          }
          if (removed.length > 0) {
            info += `\nRemoved: ${removed.join(', ')}`
          }
          scadsBotsInfo.value = info
          showAlert(`Successfully refreshed ScaDS assistants. Total: ${total}, Added: ${added.length}, Removed: ${removed.length}`)
          // Refresh topics to show new bots
          await topicsStore.fetchTopics()
          await updateStores()
        }
      }
    } catch (e) {
      console.error(e)
      showAlert('Error occurred while refreshing ScaDS bots', 'error')
    } finally {
      scadsBotsLoading.value = false
    }
  }
</script>

<template>
  <v-main>
    <v-container class="fill-height flex-column justify-center">
      <v-card max-width="700">
        <v-card-title>
          <h1 class="text-headline-sm d-flex align-center gc-1">
            <v-icon icon="mdi mdi-account-cog" start />
            {{ $t('administration') }}
          </h1>
        </v-card-title>
        <v-divider class="my-2" />
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
                         variant="flat"
                         @click="submitTopics">
                    {{ $t('saveTopicsButton', 'Save Topics') }}
                  </v-btn>
                </v-card-actions>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- ScaDS Bots Panel -->
            <v-expansion-panel :title="$t('scadsBots', 'ScaDS.AI Assistants')">
              <v-expansion-panel-text>
                <div class="mb-4">
                  {{ scadsBotsInfo }}
                </div>

                <v-card-actions>
                  <v-btn color="primary"
                         :loading="scadsBotsLoading"
                         variant="flat"
                         @click="refreshScadsBots">
                    {{ $t('refreshScadsBots', 'Refresh ScaDS Bots') }}
                  </v-btn>
                </v-card-actions>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- DB Panel -->
            <v-expansion-panel :title="$t('configureDB')">
              <v-expansion-panel-text>
                <div>
                  {{ dbInfo }}
                </div>

                <v-card-actions>
                  <v-btn color="primary"
                         :text="$t('connectDB', 'Connect to DB')"
                         variant="flat"
                         @click="connectDB" />
                  <template v-if="dbConnected">
                    <v-btn color="primary"
                           :text="$t('validateSchema', 'Validate Schema')"
                           variant="flat"
                           @click="validateSchema" />
                    <v-btn color="primary"
                           :text="$t('dropSchema', 'Drop Schema')"
                           variant="flat"
                           @click="dropSchema" />
                    <v-btn color="primary"
                           :text="$t('createSchema', 'Create Schema')"
                           variant="flat"
                           @click="createSchema" />
                    <v-btn color="primary"
                           :text="$t('loadSchema', 'Load Schema')"
                           variant="flat"
                           @click="loadSchema" />
                    <v-btn color="primary"
                           :text="$t('loadData', 'Load Data')"
                           variant="flat"
                           @click="loadData" />
                  </template>
                </v-card-actions>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Configuration Settings Panel -->
            <v-expansion-panel :title="$t('configurationSettings', 'Configuration Settings')">
              <v-expansion-panel-text>
                <v-card-actions class="mb-4">
                  <v-btn color="primary"
                         :loading="configLoading"
                         variant="flat"
                         @click="fetchConfig">
                    {{ $t('loadConfiguration', 'Load Configuration') }}
                  </v-btn>
                  <v-btn color="success"
                         :loading="configLoading"
                         variant="flat"
                         @click="saveConfig">
                    {{ $t('saveConfiguration', 'Save Configuration') }}
                  </v-btn>
                  <v-btn color="info"
                         variant="flat"
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
                <!--
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
                -->

                <!-- Form Edit Mode -->
                <div>
                  <v-card v-if="Object.keys(configValues).length === 0" flat>
                    <v-card-text class="text-center">
                      {{ $t('loadConfigurationHint', 'Click "Load Configuration" to view and edit settings') }}
                    </v-card-text>
                  </v-card>

                  <template v-for="(value, configKey) in configValues" v-else :key="configKey">
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
                <div v-if="purposes">
                  <h3 class="mb-2">Purposes</h3>
                  <v-card v-for="purpose in purposes" :key="purpose.idpurposes" class="mb-4">
                    <v-card-title class="d-flex flex-row">
                      <h2 class="text-h6">
                        {{ purpose.code }}
                      </h2>
                      <v-btn class="ml-auto"
                             icon="mdi mdi-plus"
                             variant="text"
                             @click="addModelToPurpose(purpose)" />
                    </v-card-title>
                    <v-card-text>
                      <v-list variant="outlined">
                        <VueDraggable v-model="purpose.models">
                          <v-list-item v-for="(model, i) in purpose.models"
                                       :key="i"
                                       class="mb-2"
                                       style="cursor:grab">
                            <v-list-item-title class="d-flex flex-row align-center justify-space-between">
                              <div class="d-flex flex-row align-center">
                                <v-icon class="mr-2" icon="mdi mdi-drag" />
                                <span class="mr-2">{{ i+1 }}.</span>
                                <v-text-field v-if="editing == purpose.code+''+i" v-model="editingModelName" style="width: 100px" />
                                <span v-else>{{ model }}</span>
                              </div>
                              <div>
                                <v-btn v-if="editing != purpose.code+''+i" 
                                       class="ml-2"
                                       icon="mdi mdi-pencil"
                                       variant="text"
                                       @click="editing = purpose.code+''+i; editingModelName = model" />
                                <v-btn v-else
                                       class="ml-2"
                                       icon="mdi mdi-check"
                                       variant="text"
                                       @click="editing = ''; editModelName(purpose, i, editingModelName || model)" />
                                <v-btn class="ml-2"
                                       icon="mdi mdi-close"
                                       variant="text"
                                       @click="removeModelFromPurpose(purpose, i)" />
                              </div>
                            </v-list-item-title>
                          </v-list-item>
                        </VueDraggable>
                      </v-list>
                    </v-card-text>
                  </v-card>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
      </v-card>

      <v-card class="mt-4" max-width="700">
        <v-card-title>
          <h1 class="text-headline-sm d-flex align-center gc-1">
            <v-icon icon="mdi mdi-timeline-text-outline" start />
            {{ $t('changelog') }}
          </h1>
        </v-card-title>
        <v-divider class="my-2" />
        <v-card-text>
          <VueMarkdown class="markdown" :source="changeLog" />
        </v-card-text>
      </v-card>
    </v-container>
  </v-main>
</template>

<style scoped lang="scss">
  .font-family-monospace :deep(.v-field__input) {
    font-family: 'Source Code Pro', monospace;
    font-size: .9rem
  }
</style>
