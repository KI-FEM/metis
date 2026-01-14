<script setup lang="ts">
  // A dialog to debug chat storage and user memory information
  import { computed } from 'vue'
  import { useChatStore } from '@/stores/chat'
  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue'

  const showDialog = defineModel<boolean>({default: false})

  const chatStore = useChatStore()


  const chatStorage = computed(() => chatStore.currentChat?.storage || {})
  const userMemory = computed(() => chatStore.currentChat?.storage?.user_memory || null)

  const hasData = computed(() => {
    const hasStorage = Object.keys(chatStorage.value).length > 0
    const hasMemory = !!userMemory.value
    return hasStorage || hasMemory
  })

  function formatStorageKey(key: string): string {
    return key
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  function formatStorageValue(value: unknown): string | object {
    if (typeof value === 'object' && value !== null) {
      return value // Return the object for tree display
    }
    return String(value)
  }

  function isJsonObject(value: unknown): boolean {
    return typeof value === 'object' && value !== null
  }

  function isJsonArray(value: unknown): boolean {
    return Array.isArray(value)
  }

  async function copyToClipboard() {
    const data = {
      chatStorage: chatStorage.value,
      userMemory: userMemory.value
    }
    
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2))
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
    }
  }
</script>

<template>
  <v-dialog v-model="showDialog" max-width="600px" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">
          fas fa-database
        </v-icon>
        Storage Information
        <v-spacer />
        <DialogCloseButton class="ms-auto" @click="showDialog = false" />
      </v-card-title>

      <v-card-text>
        <v-container>
          <!-- Chat Storage Section -->
          <div class="mb-6">
            <h3 class="text-h6 mb-3 d-flex align-center">
              <v-icon class="mr-2">
                fas fa-comments
              </v-icon>
              Chat Storage
            </h3>
            
            <v-card class="mb-3" variant="outlined">
              <v-card-text>
                <div v-if="chatStorage && Object.keys(chatStorage).length > 0">
                  <div v-for="(value, key, index) in chatStorage"
                       :key="key"
                       class="mb-2">
                    <div class="d-flex align-start">
                      <strong class="text-primary mr-2 flex-shrink-0" style="min-width: 120px;">
                        {{ formatStorageKey(String(key)) }}:
                      </strong>
                      <div class="text-body-2 flex-grow-1">
                        <div v-if="isJsonObject(value)" class="json-tree">
                          <!-- JSON Object/Array Tree Display -->
                          <div v-if="isJsonArray(value)" class="ml-2">
                            <div class="text-caption text-medium-emphasis mb-1">
                              Array ({{ (value as unknown[]).length }} items):
                            </div>
                            <v-expansion-panels class="json-expansion" variant="accordion">
                              <v-expansion-panel v-for="(item, arrayIndex) in (value as unknown[]).slice(0, 10)"
                                                 :key="arrayIndex"
                                                 class="mb-1">
                                <v-expansion-panel-title class="py-2">
                                  <span class="text-caption">
                                    Item {{ arrayIndex }}
                                  </span>
                                </v-expansion-panel-title>
                                <v-expansion-panel-text>
                                  <div v-if="isJsonObject(item)">
                                    <div v-for="(nestedValue, nestedKey) in item as Record<string, unknown>"
                                         :key="nestedKey"
                                         class="d-flex align-start mb-1">
                                      <strong class="text-caption mr-2" style="min-width: 100px;">
                                        {{ nestedKey }}:
                                      </strong>
                                      <span class="text-caption">
                                        {{ nestedValue === null ? 'null' : String(nestedValue) }}
                                      </span>
                                    </div>
                                  </div>
                                  <div v-else class="text-caption">
                                    {{ String(item) }}
                                  </div>
                                </v-expansion-panel-text>
                              </v-expansion-panel>
                              <div v-if="(value as unknown[]).length > 10" class="text-caption text-medium-emphasis mt-2">
                                ... and {{ (value as unknown[]).length - 10 }} more items
                              </div>
                            </v-expansion-panels>
                          </div>
                          <div v-else class="ml-2">
                            <div class="text-caption text-medium-emphasis mb-1">
                              Object:
                            </div>
                            <div v-for="(nestedValue, nestedKey) in value as unknown as Record<string, unknown>"
                                 :key="nestedKey"
                                 class="d-flex align-start mb-1">
                              <strong class="text-caption mr-2" style="min-width: 100px;">
                                {{ nestedKey }}:
                              </strong>
                              <span class="text-caption">
                                {{ nestedValue === null ? 'null' : String(nestedValue) }}
                              </span>
                            </div>
                          </div>
                        </div>
                        <span v-else>
                          {{ formatStorageValue(value) }}
                        </span>
                      </div>
                    </div>
                    <v-divider v-if="index < Object.keys(chatStorage).length - 1" class="mt-2" />
                  </div>
                </div>
                <div v-else class="text-body-2 text-medium-emphasis">
                  No storage data available
                </div>
              </v-card-text>
            </v-card>
          </div>

          <!-- User Memory Section -->
          <div>
            <h3 class="text-h6 mb-3 d-flex align-center">
              <v-icon class="mr-2">
                fas fa-brain
              </v-icon>
              User Memory
            </h3>
            
            <v-card variant="outlined">
              <v-card-text>
                <div v-if="userMemory">
                  <div class="text-body-2 whitespace-pre-wrap">
                    {{ userMemory }}
                  </div>
                </div>
                <div v-else class="text-body-2 text-medium-emphasis">
                  No user memory stored
                </div>
              </v-card-text>
            </v-card>
          </div>

          <!-- Actions -->
          <div class="mt-4 d-flex gap-2">
            <v-btn :disabled="!hasData"
                   size="small"
                   variant="outlined"
                   @click="copyToClipboard">
              <v-icon left>
                fas fa-copy
              </v-icon>
              Copy to Clipboard
            </v-btn>
            
            <v-btn size="small"
                   variant="outlined"
                   @click="showDialog = false">
              <v-icon left>
                fas fa-times
              </v-icon>
              Close
            </v-btn>
          </div>
        </v-container>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.whitespace-pre-wrap {
  white-space: pre-wrap;
  word-break: break-word;
}

.json-tree {
  font-family: 'Courier New', monospace;
  background-color: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
  padding: 8px;
  margin-top: 4px;
}

.json-expansion {
  background: transparent;
}

.json-expansion .v-expansion-panel {
  margin-bottom: 4px;
}

.json-expansion .v-expansion-panel-text__wrapper {
  padding: 8px 16px;
}

.json-expansion .v-expansion-panel-title {
  min-height: 32px;
  padding: 4px 16px;
}
</style>
