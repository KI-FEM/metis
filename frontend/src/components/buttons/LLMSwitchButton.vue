<script setup lang="ts">
  import {useTheme} from 'vuetify'
  import {useI18n} from 'vue-i18n'
  import {useTopicsStore} from '@/stores/topics.ts'
  import {useChatStore} from '@/stores/chat.ts'

  import {computed, onMounted, ref, watch} from 'vue'

  const topicsStore = useTopicsStore()
  const chatStore = useChatStore()
  const theme = useTheme()
  const {locale, t} = useI18n()

  // Function to set the LLM purpose instead of the model ID
  function setModelPurpose(purpose: string) {
    if (!purpose) return
    chatStore.setChatStorage({llm_purpose: purpose})
  }

  // Get default purpose based on locale
  const getDefaultPurpose = computed(() => locale.value === 'de' ? 'de' : 'normal')

  const opened = ref(false)
  const purposes = ref<string[]>(Object.keys(chatStore.availableAIPurposes))
  // Initialize with empty string, will be set in onMounted
  const selectedPurpose = ref<string>('')

  onMounted(() => {
    purposes.value = Object.keys(chatStore.availableAIPurposes)

    // Now set the selectedPurpose
    const defaultPurpose = getDefaultPurpose.value
    const storagePurpose = chatStore.getSelectedLLMPurpose()
    if (storagePurpose) {
      // storage contains purpose
      selectedPurpose.value = storagePurpose
    } else {
      const storageModel = chatStore.getSelectedLLMPurpose()
      if (storageModel) {
        // storage contains model (old storage)
        // find purpose of storageModel
        const purpose = chatStore.availableAIPurposes.find(p => p.id === storageModel)
        if (purpose) {
          selectedPurpose.value = purpose.id
        } else {
          selectedPurpose.value = purposes.value.find(p => p === defaultPurpose) || purposes.value[0] || ''
        }
      } else {
        selectedPurpose.value = purposes.value.find(p => p === defaultPurpose) || purposes.value[0] || ''
      }
    }

    // Set the initial purpose
    setModelPurpose(selectedPurpose.value)
  })

  // Interface for the purpose items
  interface PurposeItem {
    title: string;
    description: string;
    value: string;
    icon: string;
  }

  watch(selectedPurpose, () => {
    if (!selectedPurpose.value) return
    // Extract the value if it's a PurposeItem object
    const purposeValue = typeof selectedPurpose.value === 'string'
      ? selectedPurpose.value
      : (selectedPurpose.value as unknown as PurposeItem).value

    // Set the purpose in storage
    setModelPurpose(purposeValue)
  })

  // Localized purpose names and descriptions
  const getPurposeTitle = (purpose: string) => {
    const key = `llmPurpose${purpose.charAt(0).toUpperCase() + purpose.slice(1)}`
    return t(key)
  }

  const getPurposeDescription = (purpose: string) => {
    const key = `llmPurpose${purpose.charAt(0).toUpperCase() + purpose.slice(1)}Desc`
    return t(key)
  }

  // Get icon for purpose
  const getPurposeIcon = (purpose: string) => {
    switch (purpose) {
      case 'normal':
        return 'fas fa-check-circle' // Checkmark for optimal/standard
      case 'thinking':
        return 'fas fa-brain' // Brain for analytical thinking
      case 'de':
        return 'fas fa-language' // Language icon for German
      default:
        return 'fas fa-robot' // Default robot icon
    }
  }

  // Create items with localized titles, descriptions and icons for v-select
  const localizedPurposes = computed<PurposeItem[]>(() =>
    purposes.value.map(purpose => ({
      title: getPurposeTitle(purpose),
      description: getPurposeDescription(purpose),
      value: purpose,
      icon: getPurposeIcon(purpose)
    }))
  )
</script>

<template>
  <v-btn :aria-label="$t('chatSettings')"
         class="text-label-sm"
         color="primary"
         icon
         variant="outlined">
    <v-icon icon="fas fa-chevron-up" size="x-small" />
    <v-tooltip activator="parent" :text="$t('chatSettings')" />
    <v-menu v-model="opened"
            activator="parent"
            :close-on-content-click="false"
            :theme="theme.global.name.value">
      <v-list>
        <v-list-item v-if="topicsStore.selectedTopic && topicsStore.selectedTopic.features.includes('streaming')">
          <v-switch v-model="chatStore.streaming"
                    class="mb-n6"
                    color="primary"
                    inset
                    :label="$t('streaming')" />
        </v-list-item>
        <v-list-item>
          <v-select v-model="selectedPurpose"
                    item-title="title"
                    item-value="value"
                    :items="localizedPurposes"
                    :label="$t('changeLLM')">
            <template #selection="{ item }">
              <div class="d-flex align-center">
                {{ item.props.title }}
              </div>
            </template>
            <template #item="{ props, item }">
              <v-list-item v-bind="props">
                <template #prepend>
                  <v-icon :icon="item.raw.icon" />
                </template>
                <template #title>
                  <span>{{ item.raw.title }}</span>
                </template>
                <template #subtitle>
                  <span class="text-caption">{{ item.raw.description }}</span>
                </template>
              </v-list-item>
            </template>
          </v-select>
        </v-list-item>
      </v-list>
    </v-menu>
  </v-btn>
</template>

<style lang="scss" scoped>

</style>
