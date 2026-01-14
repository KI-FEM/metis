<script setup lang="ts">
  import {computed, onMounted, ref, watch} from 'vue'
  import {useI18n} from 'vue-i18n'

  import {useChatStore} from '@/stores/chat.ts'
  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue'

  const {locale, t} = useI18n()
  const chatStore = useChatStore()

  const showDialog = defineModel<boolean>({default: false})
  const selectedPurpose = ref<string>('')


  // Function to set the LLM purpose instead of the model ID
  function setModelPurpose(purpose: string) {
    if (!purpose) return
    chatStore.setChatStorage({llm_purpose: purpose})
  }

  // Get default purpose based on locale
  const getDefaultPurpose = computed(() => locale.value === 'de' ? 'german' : 'optimal')

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

  // Create items with localized titles, descriptions and icons for v-select
  const localizedPurposes = computed<PurposeItem[]>(() => 
    chatStore.availableAIPurposes.filter(purpose => purpose.healthy).map(purpose => ({
      title: purpose.label[locale.value],
      description: purpose.description[locale.value],
      value: purpose.id,
      icon: purpose.icon
    } as PurposeItem))
  )


  onMounted(() => {
    // Now set the selectedPurpose
    const defaultPurpose = getDefaultPurpose.value
    const storagePurpose = chatStore.getSelectedLLMPurpose()
    if (storagePurpose) {
      // storage contains purpose
      selectedPurpose.value = storagePurpose
    } else {
      // storage does not contain purpose
      selectedPurpose.value = defaultPurpose
    }
    
    // Set the initial purpose
    setModelPurpose(selectedPurpose.value)
  })

  // const selectedLLM = ref(topicsStore.availableModels.length > 0 ? topicsStore.availableModels[0].label : '')
  //
</script>

<template>
  <v-dialog v-model="showDialog" max-width="700">
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <v-icon icon="mdi mdi-creation-outline" start />
          <h1 class="text-headline-sm">
            {{ $t('selectAiModel') }}
          </h1>
          <DialogCloseButton class="ms-auto" @click="showDialog = false" />
        </v-card-title>
      </v-card-item>
      <v-card-text>
        <p>{{ $t('selectAiModelIntro1') }}</p>
        <p>{{ $t('selectAiModelIntro2') }}</p>
        <p>{{ $t('selectAiModelIntro3') }}</p>
        <v-select v-model="selectedPurpose"
                  class="mt-8 mb-4"
                  hide-details
                  :items="localizedPurposes"
                  :label="$t('selectAiModel')">
          <template #selection="{ item }">
            <div class="d-flex align-center">
              <v-icon :icon="item.raw.icon" size="small" start />
              {{ item.title }}
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
        <p>{{ $t('selectAiModelIntro4') }}</p>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

