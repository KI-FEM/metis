<script setup lang="ts">
  import {ref, computed} from 'vue'
  import {useRouter, useRoute} from 'vue-router'
  import {useDisplay} from 'vuetify'
  import {useI18n} from 'vue-i18n'
  import VueMarkdown from 'vue-markdown-render'

  import type {Chat} from '@/types'
  import type {components} from '@/types_api'

  import {useTopicsStore} from '@/stores/topics'
  import {useChatStore} from '@/stores/chat'

  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue'

  const router = useRouter()
  const route = useRoute()
  const {xs} = useDisplay()
  const {locale} = useI18n()
  const topicsStore = useTopicsStore()
  const chatStore = useChatStore()

  const showBackupDialog = ref(false)
  const selectedExport = ref<'single' | 'topic' | 'all'>()
  const selectedImport = ref<File>()
  const isLoadingImport = ref(false)
  const isErrorImport = ref(false)
  const showDeleteDialog = ref(false)
  const showStreamingDialog = ref(false)

  const selectedModule = computed(() => topicsStore.selectedTopic?.modules.find(module => module.id === route.params.chatId) as components['schemas']['Skill'])
  const selectedLevel = computed(() => selectedModule.value?.levels.find(level => level.id === topicsStore.storedModuleLevelId(selectedModule.value?.id)))

  function getChatTitle(chat: Chat) {
    const title = chat.title || chatStore.getDefaultChatTitle()
    return title.length > 48 ? `${title.slice(0, 48)}...` : title // if longer than 48 chars, cut it off
  }

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
    if (selectedTopic.modules.length)
      await router.push({name: 'modules', params: {endpoint: selectedTopic.endpoint}})
    else await router.push({name: 'topics'})
    chatStore.deleteCurrentChat(selectedTopic.endpoint, currentChat.id)
  }

  async function deleteAllChats() {
    // store selectedTopic locally as it is not available any longer after navigation
    const selectedTopic = topicsStore.selectedTopic
    if (!selectedTopic)
      return
    console.log(selectedTopic.modules.length)
    if (selectedTopic.modules.length)
      await router.push({name: 'modules', params: {endpoint: selectedTopic.endpoint}})
    else await router.push({name: 'topics'})
    chatStore.deleteModuleChats(selectedTopic.endpoint)
  }
</script>

<template>
  <v-card id="topic-card" tag="header" width="100%">
    <v-card-item>
      <v-card-title class="d-flex align-center ga-3 text-headline-sm text-sm-headline-md text-md-headline-lg">
        <v-icon icon="mdi mdi-book-open-variant" :style="{color: topicsStore.selectedTopic?.color || undefined}" />
        <v-skeleton-loader :loading="topicsStore.isFetching" type="heading" :width="xs ? '80%' : '60%'">
          <h2 style="font-size: inherit; font-weight: inherit;">
            {{ topicsStore.selectedTopic?.title[locale] }}
          </h2>
        </v-skeleton-loader>
      </v-card-title>
    </v-card-item>
    <v-card-text>
      <v-skeleton-loader :loading="topicsStore.isFetching" type="sentences">
        <VueMarkdown class="markdown" :source="topicsStore.selectedTopic?.long_description[locale]" />
      </v-skeleton-loader>
    </v-card-text>
    <v-card-actions v-if="$route.name === 'chat'">
      <v-skeleton-loader class="w-100 align-end ga-2" :loading="topicsStore.isFetching" type="button@2">
        <template v-if="selectedModule">
          <v-chip class="bg-secondary"
                  prepend-icon="fas fa-graduation-cap"
                  :to="{name: 'modules'}">
            <span class="sr-only">{{ $t('actionModule') }}:</span> {{ selectedModule?.title[locale] }}
          </v-chip>
          <v-chip class="bg-tertiary"
                  prepend-icon="fas fa-flag-checkered"
                  :to="{name: 'modules'}">
            <span class="sr-only">{{ $t('actionLevel') }}:</span> {{ selectedLevel?.title[locale] }}
          </v-chip>
        </template>
        <template v-else>
          <v-chip class="bg-secondary"
                  prepend-icon="fas fa-clock-rotate-left">
            {{ $t('actionChatHistory') }}
            <v-menu activator="parent" open-on-click>
              <v-list>
                <v-list-item v-for="chat in chatStore.topicChats"
                             :key="chat.id"
                             :subtitle="chat.id"
                             :title="getChatTitle(chat)"
                             :to="{name: 'chat', params: {chatId: chat.id}}" />
              </v-list>
            </v-menu>
          </v-chip>
          <v-chip class="bg-tertiary"
                  prepend-icon="far fa-comment"
                  :text="$t('actionNewChat')"
                  :to="{name: 'chat', params: {chatId: 'new'}}" />
        </template>
        <div class="ms-auto">
          <v-btn :aria-label="$t('chatOptions')" icon>
            <v-icon icon="fas fa-ellipsis-vertical" />
            <v-tooltip activator="parent" :text="$t('chatOptions')" />
            <v-menu activator="parent" max-width="700">
              <v-list>
                <!-- <v-list-item prepend-icon="far fa-face-smile-wink" title="Emojies" /> -->
                <!-- <v-list-item prepend-icon="far fa-message" title="Nachrichten-Bubble" /> -->
                <v-list-item prepend-icon="far fa-floppy-disk"
                             :title="$t('chatOptionsBackup')"
                             @click="showBackupDialog = true" />
                <v-list-item prepend-icon="far fa-trash-can"
                             :title="$t('chatOptionsDelete')"
                             @click="showDeleteDialog = true" />
                <v-list-item :disabled="!topicsStore.selectedTopic?.features.includes('streaming')"
                             prepend-icon="fas fa-bars-staggered"
                             :title="$t('chatOptionsStreaming')"
                             @click="showStreamingDialog = true" />
              </v-list>
            </v-menu>
          </v-btn>
        </div>
      </v-skeleton-loader>
    </v-card-actions>
  </v-card>

  <v-dialog v-model="showBackupDialog"
            max-width="700"
            :persistent="isLoadingImport"
            @after-leave="() => {selectedImport = undefined; isErrorImport = false}">
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <v-icon icon="far fa-floppy-disk" start />
          <h1 class="text-headline-sm">
            {{ $t('chatOptionsBackup') }}
          </h1>
          <DialogCloseButton class="ms-auto" :disabled="isLoadingImport" @click="showBackupDialog = false" />
        </v-card-title>
      </v-card-item>
      <v-card-text>
        <h2 class="mb-2 text-title-lg">
          {{ $t('chatOptionsBackupExport') }}
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
            {{ $t('chatOptionsDelete') }}
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

  <v-dialog v-model="showStreamingDialog" max-width="700">
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <v-icon icon="fas fa-bars-staggered" start />
          <h1 class="text-headline-sm">
            {{ $t('chatOptionsStreaming') }}
          </h1>
          <DialogCloseButton class="ms-auto" @click="showStreamingDialog = false" />
        </v-card-title>
      </v-card-item>
      <v-card-text>
        <p>{{ $t('chatOptionsStreamingIntro1') }}</p>
        <p>{{ $t('chatOptionsStreamingIntro2') }}</p>
        <p>{{ $t('chatOptionsStreamingIntro3') }}</p>
        <v-switch v-model="chatStore.streaming"
                  hide-details
                  :label="chatStore.streaming ? $t('chatOptionsStreamingActive') : $t('chatOptionsStreamingInactive')" />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style lang="scss" scoped>
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

  #topic-card.to-front {
    box-shadow: 0 0 10px 5px rgba(var(--v-theme-accent), 0.4), 0 0 20px 10px rgba(var(--v-theme-accent), 0.3);
  }
</style>
