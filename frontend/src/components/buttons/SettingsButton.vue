<script setup lang="ts">
  import {ref} from 'vue'
  import {useDisplay} from 'vuetify'
  import {useRouter} from 'vue-router'
  import {useI18n} from 'vue-i18n'

  import type {Locale, LocalizedString} from '@/types.ts'
  import type {components} from '@/types_api.ts'

  import {useTopicsStore} from '@/stores/topics'
  import {useChatStore} from '@/stores/chat'

  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue'

  const responsePreferences: {
    id: keyof components['schemas']['ResponsePreferences'],
    label: LocalizedString,
    low: LocalizedString,
    medium: LocalizedString,
    high: LocalizedString
  }[] = [
    {
      id: 'detail',
      label: {de: 'Detailgrad', en: 'Level of detail'},
      low: {de: 'knapp', en: 'brief'},
      medium: {de: 'ausführlich', en: 'thorough'},
      high: {de: 'tiefgründig', en: 'in-depth'}
    },
    {
      id: 'illustration',
      label: {de: 'Anschaulichkeit', en: 'Illustration level'},
      low: {de: 'abstrakt', en: 'abstract'},
      medium: {de: 'beispielhaft', en: 'illustrative'},
      high: {de: 'narrativ', en: 'narrative'}
    },
    {
      id: 'language_style',
      label: {de: 'Sprachstil', en: 'Language style'},
      low: {de: 'umgangssprachlich', en: 'colloquial'},
      medium: {de: 'neutral', en: 'neutral'},
      high: {de: 'eloquent', en: 'eloquent'}
    },
    {
      id: 'humour',
      label: {de: 'Humor', en: 'Humour'},
      low: {de: 'ernst', en: 'serious'},
      medium: {de: 'heiter', en: 'light-hearted'},
      high: {de: 'witzig', en: 'witty'}
    },
    {
      id: 'creativity',
      label: {de: 'Kreativität', en: 'Creativity'},
      low: {de: 'konventionell', en: 'conventional'},
      medium: {de: 'originell', en: 'original'},
      high: {de: 'phantasievoll', en: 'imaginative'}
    },
    {
      id: 'emojis',
      label: {de: 'Emojis', en: 'Emojis'},
      low: {de: 'sparsam', en: 'sparse'},
      medium: {de: 'moderat', en: 'moderate'},
      high: {de: 'reichlich', en: 'abundant'}
    }
  ]

  const router = useRouter()
  const {locale} = useI18n()
  const topicsStore = useTopicsStore()
  const chatStore = useChatStore()
  const {xs} = useDisplay()

  const showPreferencesDialog = ref(false)
  const showBackupDialog = ref(false)
  const selectedExport = ref<'single' | 'topic' | 'all'>()
  const selectedImport = ref<File>()
  const isLoadingImport = ref(false)
  const isErrorImport = ref(false)
  const showDeleteDialog = ref(false)

  function saveBackup() {
    if (!topicsStore.selectedTopic)
      return
    const backup = {
      timestamp: new Date().toISOString(),
      chats: selectedExport.value === 'all' ? chatStore.allChats : {[topicsStore.selectedTopic.endpoint]: selectedExport.value === 'topic' ? chatStore.topicChats : [chatStore.currentChat]}
    }
    const blob = new Blob([JSON.stringify(backup)], {type: 'application/json'})
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `backup-${backup.timestamp.slice(0, 19).replace(/[T:]/g, '-')}.metis`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function loadBackup(file: File | File[]) {
    try {
      isErrorImport.value = false
      isLoadingImport.value = true
      if (Array.isArray(file))
        throw new Error('Only single file supported.')
      if (!file.name.endsWith('.metis'))
        throw new Error('Wrong file type.')
      const backup = JSON.parse(await file.text())
      chatStore.importChats(backup.chats)
    } catch (e) {
      isErrorImport.value = true
    } finally {
      isLoadingImport.value = false
    }
  }

  async function deleteCurrentChat() {
    // store selectedTopic and current chat locally as it is not available any longer after navigation
    const selectedTopic = topicsStore.selectedTopic
    const currentChat = chatStore.currentChat
    if (!selectedTopic || !currentChat)
      return
    if (selectedTopic.modules.length && selectedTopic.type === 'skills')
      await router.push({name: 'modules', params: {endpoint: selectedTopic.endpoint}})
    else await router.push({name: 'chat', params: {endpoint: selectedTopic.endpoint}})
    chatStore.deleteCurrentChat(selectedTopic.endpoint, currentChat.id)
    showDeleteDialog.value = false
  }

  async function deleteAllChats() {
    // store selectedTopic locally as it is not available any longer after navigation
    const selectedTopic = topicsStore.selectedTopic
    if (!selectedTopic)
      return
    console.log(selectedTopic.modules.length)
    if (selectedTopic.modules.length && selectedTopic.type === 'skills')
      await router.push({name: 'modules', params: {endpoint: selectedTopic.endpoint}})
    else await router.push({name: 'chat', params: {endpoint: selectedTopic.endpoint}})
    chatStore.deleteModuleChats(selectedTopic.endpoint)
    showDeleteDialog.value = false
  }
</script>

<template>
  <v-btn :aria-label="$t('openSettings')" icon variant="text">
    <v-icon icon="fas fa-cog" />
    <v-tooltip activator="parent" :text="$t('openSettings')" />
    <v-menu activator="parent"
            :close-on-content-click="false"
            open-on-click>
      <v-list>
        <v-list-item prepend-icon="fas fa-sliders"
                     :title="$t('chatSettings')"
                     @click="showPreferencesDialog = true" />
        <v-list-item prepend-icon="far fa-floppy-disk"
                     :title="$t('chatBackup')"
                     @click="showBackupDialog = true" />
        <v-list-item prepend-icon="far fa-trash-can"
                     :title="$t('chatDelete')"
                     @click="showDeleteDialog = true" />
      </v-list>
    </v-menu>
  </v-btn>

  <v-dialog v-model="showPreferencesDialog" max-width="700" scrollable>
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <v-icon icon="fas fa-sliders" start />
          <h1 class="text-headline-sm">
            {{ $t('chatSettings') }}
          </h1>
          <DialogCloseButton class="ms-auto" @click="showPreferencesDialog = false" />
        </v-card-title>
      </v-card-item>
      <v-card-text>
        <h2 class="mb-2 text-title-lg">
          {{ $t('chatOptionsResponsePreferences') }}
        </h2>
        <p>{{ $t('chatOptionsResponsePreferencesIntro1') }}</p>
        <p>{{ $t('chatOptionsResponsePreferencesIntro2') }}</p>
        <template v-for="preference in responsePreferences"
                  :key="preference.id">
          <label class="font-weight-bold" :for="'pref-slider-' + preference.id">
            {{ preference.label[locale as Locale] }}
          </label>
          <v-slider :id="'pref-slider-' + preference.id"
                    v-model="chatStore.responsePreferences[preference.id]"
                    class="mt-1 mb-6"
                    hide-details
                    max="4"
                    show-ticks
                    step="1"
                    :ticks="{0: preference.low[locale as Locale], 1: '', 2: xs ? '' : preference.medium[locale as Locale], 3: '', 4: preference.high[locale as Locale]}" />
        </template>
        <v-divider class="my-3" />
        <h2 class="mb-2 text-title-lg">
          {{ $t('chatOptionsStreaming') }}
        </h2>
        <p>{{ $t('chatOptionsStreamingIntro1') }}</p>
        <p>{{ $t('chatOptionsStreamingIntro2') }}</p>
        <p>{{ $t('chatOptionsStreamingIntro3') }}</p>
        <v-switch v-model="chatStore.streaming"
                  hide-details
                  inset
                  :label="$t('chatOptionsStreaming')"
                  true-icon="fas fa-check" />
        <!--        <v-divider class="my-3" />-->
        <!--        <h2 class="mb-2 text-title-lg">-->
        <!--          {{ $t('chatOptionsChatBubbles') }}-->
        <!--        </h2>-->
        <!--        <ChatBubble :message="{message: 'Beispiel', sender: 'assistant', buttons:[], complete:true}" />-->
      </v-card-text>
    </v-card>
  </v-dialog>

  <v-dialog v-model="showBackupDialog"
            max-width="700"
            :persistent="isLoadingImport"
            @after-leave="() => {selectedImport = undefined; isErrorImport = false}">
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <v-icon icon="far fa-floppy-disk" start />
          <h1 class="text-headline-sm">
            {{ $t('chatBackup') }}
          </h1>
          <DialogCloseButton class="ms-auto" :disabled="isLoadingImport" @click="showBackupDialog = false" />
        </v-card-title>
      </v-card-item>
      <v-card-text>
        <h2 class="mb-2 text-title-lg">
          {{ $t('chatBackup') }}
        </h2>
        <p>{{ $t('chatOptionsBackupExportIntro') }}</p>
        <v-sheet class="backup-area">
          <v-row align="center" class="my-0" justify="space-evenly">
            <v-col cols="auto">
              <v-radio-group v-model="selectedExport" :disabled="isLoadingImport" hide-details>
                <v-radio :label="$t('chatOptionsBackupExportSingle')" value="single" />
                <v-radio :label="$t('chatOptionsBackupExportTopic')" value="topic" />
                <v-radio :label="$t('chatOptionsBackupExportAll')" value="all" />
              </v-radio-group>
            </v-col>
            <v-col cols="auto">
              <v-btn append-icon="fas fa-download"
                     :disabled="!selectedExport || isLoadingImport"
                     :text="$t('chatOptionsBackupSave')"
                     variant="outlined"
                     @click="saveBackup" />
            </v-col>
          </v-row>
        </v-sheet>
      </v-card-text>
      <v-divider />
      <v-card-text>
        <h2 class="mb-2 text-title-lg">
          {{ $t('chatOptionsBackupImport') }}
        </h2>
        <p>{{ $t('chatOptionsBackupImportIntro') }}</p>
        <v-file-upload v-model="selectedImport"
                       accept=".metis"
                       class="backup-area"
                       density="compact"
                       :disabled="isLoadingImport"
                       icon="fas fa-upload"
                       :title="$t('chatOptionsBackupSelect')"
                       @update:model-value="loadBackup">
          <template #item>
            <div class="text-center">
              <v-chip prepend-icon="far fa-file-lines"
                      style="font-weight: bold !important;"
                      :text="selectedImport?.name" />
            </div>
          </template>
        </v-file-upload>
        <div v-if="isLoadingImport" class="mt-3 text-center">
          <v-progress-circular class="me-3" color="primary" indeterminate />
          <span>{{ $t('chatOptionsBackupLoading') }}</span>
        </div>
        <v-alert v-if="isErrorImport"
                 class="mt-3 text-body-lg"
                 color="error-container"
                 type="error">
          {{ $t('chatOptionsBackupError') }}
        </v-alert>
        <v-alert v-else-if="!isLoadingImport && selectedImport"
                 class="mt-3  text-body-lg"
                 color="secondary-container"
                 type="success">
          {{ $t('chatOptionsBackupSuccess') }}
        </v-alert>
      </v-card-text>
    </v-card>
  </v-dialog>

  <v-dialog v-model="showDeleteDialog" max-width="700">
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <v-icon icon="far fa-trash-can" start />
          <h1 class="text-headline-sm">
            {{ $t('chatDelete') }}
          </h1>
          <DialogCloseButton class="ms-auto" @click="showDeleteDialog = false" />
        </v-card-title>
      </v-card-item>
      <v-card-text>
        <p>
          <I18nT keypath="chatOptionsDeleteIntro1" scope="global">
            <strong>{{ $t('chatOptionsDeleteThisChat') }}</strong><strong>{{
              $t('chatOptionsDeleteAllChats')
            }}</strong>{{ topicsStore.selectedTopic?.title[locale] }}
          </I18nT>
          <br>
          {{ $t('chatOptionsDeleteIntro2') }}
        </p>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn :text="$t('chatOptionsDeleteCancel')"
               variant="text"
               @click="showDeleteDialog = false" />
        <v-btn append-icon="far fa-trash-can"
               class="delete-button text-capitalize"
               :text="$t('chatOptionsDeleteDeleteThisChat')"
               variant="flat"
               @click="deleteCurrentChat" />
        <v-btn append-icon="far fa-trash-can"
               class="delete-button text-capitalize"
               :text="$t('chatOptionsDeleteDeleteAllChats')"
               variant="flat"
               @click="deleteAllChats" />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped lang="scss">
  :deep(.backup-area) {
    background: rgb(var(--v-theme-surface));
    border: 2px dashed rgb(var(--v-theme-outline-variant));
    border-radius: 12px;

    .v-file-upload-icon, .v-file-upload-title {
      font-size: .875rem;
      font-weight: normal;
      letter-spacing: .14px;
    }
  }

  .delete-button {
    background: rgb(var(--v-theme-error)) !important;
    color: rgb(var(--v-theme-on-error)) !important;
    text-transform: capitalize;
  }
</style>
