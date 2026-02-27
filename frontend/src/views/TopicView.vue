<script setup lang="ts">
  import {ref, computed} from 'vue'
  import {useI18n} from 'vue-i18n'
  import VueMarkdown from 'vue-markdown-render'

  import type {components} from '@/types_api.ts'

  import {useTopicsStore} from '@/stores/topics'

  import TopicCard from '@/components/TopicCard.vue'

  const {locale} = useI18n()
  const topicsStore = useTopicsStore()

  const selectedModuleId = ref<components['schemas']['Skill']['levels'][0]['id']>()
  const showLearningObjectiveDialog = ref(false)
  const customLearningObjectiveInput = ref('')

  const selectedModule = computed(() => {
    if (topicsStore.selectedTopic?.type == 'basic') return undefined
    if (!selectedModuleId.value) return undefined
    return topicsStore.selectedTopic?.modules.find(module => module.id === selectedModuleId.value) as components['schemas']['Skill']
  })
  const selectedLevelId = computed({
    get() {
      return topicsStore.storedModuleLevelId(selectedModuleId.value)
    },
    set(levelId: string) {
      if (selectedModuleId.value)
        topicsStore.storeModuleLevel(selectedModuleId.value, levelId)
    }
  })
  const selectedLevel = computed(() => selectedModule.value?.levels.find(level => level.id === selectedLevelId.value))

  function getCustomLearningObjective() {
    return topicsStore.storedModuleLevelObjective(selectedModuleId.value, selectedLevelId.value)
  }

  function getDefaultLearningObjective() {
    return selectedLevel.value?.learning_goals[locale.value] ?? ''
  }

  function adjustLearningObjective() {
    customLearningObjectiveInput.value = getCustomLearningObjective()?.text ?? getDefaultLearningObjective()
    showLearningObjectiveDialog.value = true
  }

  function saveCustomLearningObjective() {
    topicsStore.storeCustomLearningObjective(selectedModuleId.value!, selectedLevelId.value!, customLearningObjectiveInput.value, locale.value)
    showLearningObjectiveDialog.value = false
  }

  // TODO: if route contains param moduleId, open it (and maybe update route when different module opened)
</script>

<template>
  <TopicCard />

  <div id="configure-topic">
    <div class="mt-6 mb-2 mx-auto" style="max-width: 800px">
      <!-- TODO : support \n linebreaks of i18n strings -->
      <h3 class="text-title-lg">
        {{ $t('configureTopic') }}
      </h3>
      {{ $t('topicsIntro', [topicsStore.selectedTopic?.modules.length]) }}
    </div>

    <v-expansion-panels v-model="selectedModuleId" flat tile>
      <v-expansion-panel v-for="(module, moduleIndex) in topicsStore.selectedTopic?.modules as components['schemas']['Skill'][]"
                         :key="module.id"
                         class="mt-3"
                         :value="module.id">
        <v-card class="mx-auto"
                max-width="800"
                tag="li"
                variant="outlined">
          <v-expansion-panel-title class="py-0 ps-0 pe-4 ga-0">
            <div class="d-flex">
              <v-img v-if="module.image"
                     alt=""
                     cover
                     :src="module.image"
                     width="112" />
              <div>
                <v-card-title class="text-title-md" tag="h4">
                  {{ $t('moduleTitle', {index: moduleIndex + 1, title: module.title[locale]}) }}
                </v-card-title>
                <v-card-text v-if="module.description">
                  {{ module.description[locale] }}
                </v-card-text>
              </div>
            </div>
          </v-expansion-panel-title>
          <v-expansion-panel-text class="text-center">
            <v-divider />
            <v-card-text>
              <h5 class="text-title-sm">
                {{ $t('levelTitle') }}
              </h5>
              {{ $t('levelIntro') }}
            </v-card-text>
            <v-slide-group v-model="selectedLevelId" mandatory show-arrows>
              <v-slide-group-item v-for="(level, levelIndex) in module.levels"
                                  :key="level.id"
                                  v-slot="{isSelected, select}"
                                  :value="level.id">
                <v-icon v-if="levelIndex"
                        class="my-auto"
                        color="tertiary"
                        icon="fas fa-caret-right" />
                <v-card :aria-checked="isSelected"
                        :aria-describedby="level.id + '_desc'"
                        :aria-labelledby="level.id + '_label'"
                        class="level-card"
                        :class="{'level-card-selected': isSelected}"
                        max-width="250"
                        role="radio"
                        tabindex="0"
                        variant="tonal"
                        @click="select">
                  <v-card-title class="text-label-md font-weight-bold">
                    {{ level.title[locale] }}
                  </v-card-title>
                  <v-card-text>{{ level.description[locale] }}</v-card-text>
                </v-card>
              </v-slide-group-item>
            </v-slide-group>
            <template v-if="selectedLevelId">
              <v-divider class="mt-4" />
              <v-card-text>
                <h5 class="text-title-sm">
                  {{ $t('learningObjectiveTitle') }}
                </h5>
                {{ $t('learningObjectiveIntro') }}
              </v-card-text>
              <v-alert class="mx-4 text-start" color="secondary-container" icon="fas fa-quote-right">
                <VueMarkdown class="markdown"
                             :source="getCustomLearningObjective()?.text || getDefaultLearningObjective()" />
              </v-alert>
              <v-card-text v-if="getCustomLearningObjective()" class="ma-4 pa-0 font-italic">
                {{ $t('adjustLearningObjectiveCustomized') }}
              </v-card-text>
              <v-alert v-if="getCustomLearningObjective() && getCustomLearningObjective()?.text !== getDefaultLearningObjective() && getCustomLearningObjective()?.locale !== locale"
                       class="ma-4 text-start"
                       color="error-container"
                       :text="$t('adjustLearningObjectiveLocaleMissmatch')"
                       type="warning" />
            </template>
            <v-divider class="mt-4" />
            <v-card-actions class="justify-end">
              <v-btn :aria-label="$t('closeModule')"
                     icon
                     variant="text"
                     @click="selectedModuleId = undefined">
                <v-icon icon="fas fa-close" />
                <v-tooltip activator="parent" :text="$t('closeModule')" />
              </v-btn>
              <v-spacer />
              <v-btn append-icon="fas fa-flag-checkered"
                     :disabled="!selectedLevelId"
                     :text="$t('adjustLearningObjective')"
                     variant="outlined"
                     @click="adjustLearningObjective" />
              <v-btn append-icon="fas fa-comment"
                     :disabled="!selectedLevelId"
                     :text="$t('startChat')"
                     :to="{name: 'chat', params: {chatId: selectedModuleId}}"
                     variant="flat" />
            </v-card-actions>
          </v-expansion-panel-text>
        </v-card>
      </v-expansion-panel>
    </v-expansion-panels>

    <v-dialog v-model="showLearningObjectiveDialog" max-width="700" persistent>
      <v-card>
        <v-card-item>
          <v-card-title class="me-2">
            {{ $t('adjustLearningObjective') }}
            <v-chip>{{ selectedLevel?.title[locale] }}</v-chip>
          </v-card-title>
        </v-card-item>
        <v-card-text>
          <p>
            {{
              $t('adjustLearningObjectiveIntro1', [selectedLevel?.title[locale]])
            }}
          </p>
          <p>{{ $t('adjustLearningObjectiveIntro2') }}</p>
          <p>{{ $t('adjustLearningObjectiveIntro3') }}</p>
          <v-textarea v-model.trim="customLearningObjectiveInput" class="mb-n8 mt-4" :label="$t('learningObjective')" />
        </v-card-text>
        <v-card-actions>
          <v-btn :disabled="customLearningObjectiveInput === getDefaultLearningObjective()"
                 prepend-icon="fas fa-arrow-rotate-left"
                 :text="$t('adjustLearningObjectiveReset')"
                 variant="outlined"
                 @click="customLearningObjectiveInput = getDefaultLearningObjective()" />
          <v-spacer />
          <v-btn :text="$t('adjustLearningObjectiveCancel')"
                 variant="text"
                 @click="showLearningObjectiveDialog = false" />
          <v-btn append-icon="fas fa-floppy-disk"
                 :disabled="!customLearningObjectiveInput"
                 :text="$t('adjustLearningObjectiveSave')"
                 variant="flat"
                 @click="saveCustomLearningObjective" />
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style lang="scss" scoped>
  :deep(.v-expansion-panel-text__wrapper) {
    padding: 0 !important;
  }

  .level-card {
    background: rgb(var(--v-theme-tertiary-container)) !important;
    color: rgb(var(--v-theme-on-tertiary-container)) !important;

    .v-icon {
      position: absolute;
      right: 16px;
    }
  }

  .level-card-selected {
    background: rgb(var(--v-theme-tertiary)) !important;
    color: rgb(var(--v-theme-on-tertiary)) !important;
  }

  #configure-topic.to-front {
    z-index: 2401 !important;
    background-color: rgba(var(--v-theme-surface-container), 1);
    position: relative;
    border-radius: 10px;
    box-shadow: 0 0 10px 5px rgba(var(--v-theme-accent), 0.4), 0 0 20px 10px rgba(var(--v-theme-accent), 0.4);

    & #skills-list {
      border-radius: 10px;
    }
  }


  .to-front.white-shadow {
    box-shadow: 0 0 10px 5px rgba(var(--v-theme-accent), 0.4), 0 0 20px 10px rgba(var(--v-theme-accent), 0.4);
  }

  .fit-content {
    min-width: fit-content;
  }

  .center-container:has(#chat.to-front) {
    z-index: 2000 !important;

    & .to-front {
      border-radius: 1.5rem;
      box-shadow: 0 0 10px 5px rgba(var(--v-theme-accent), 0.4), 0 0 20px 10px rgba(var(--v-theme-accent), 0.3);
    }
  }

  .center-container:has(#inspirations.to-front) {
    z-index: 2000 !important;

    & #chat {
      border-radius: 1.5rem;
      //box-shadow: 0 0 10px 5px rgba(255, 255, 255, 0.2), 0 0 20px 10px rgba(255, 255, 255, 0.19);
    }

    & .to-front {
      box-shadow: 0 0 10px 5px rgba(var(--v-theme-accent), 1), 0 0 20px 10px rgba(var(--v-theme-accent), 1),;
      //border: 1px solid rgba(var(--v-theme-tertiary));
      //background-color: rgba(var(--v-theme-primary), 1) !important;
      //color: white !important;
    }
  }
</style>
