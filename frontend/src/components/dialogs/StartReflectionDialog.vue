<script setup lang="ts">
  import {useChatStore} from '@/stores/chat.ts'
  import type {components} from '@/types_api.ts'
  import {computed, ref} from 'vue'
  import {useI18n} from 'vue-i18n'
  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue'
  import { useQuizStore } from '@/stores/quiz'

  const showDialog = defineModel<boolean>({default: false})

  const quizStore = useQuizStore()
  const chatStore = useChatStore()

  const {locale, t} = useI18n()
  const showSuccess = ref(false)
  const competences = computed(
    () => {
      const learnerModel = chatStore.currentChat?.storage.learner_model as components["schemas"]["LearnerModel-Input"];

      if (!learnerModel || !learnerModel.competences || learnerModel.competences == undefined) {
        return []
      }
      return Object.values(learnerModel.competences)
    }
  )

  const closeDialog = () => {
    selectedCompetences.value = []
    showDialog.value = false
    showSuccess.value = false
  }

  async function startReflection() {
    if (selectedCompetences.value.length == 0) {
      return
    }
    
    closeDialog()
    selectedCompetences.value = []
    await quizStore.createQuizFragment(selectedCompetences.value)
  }

  const disableReflection = computed(() => {
    return selectedCompetences.value.length == 0
  })

  const selectedCompetences = ref([] as string[])
</script>

<template>
  <v-dialog v-model="showDialog" max-width="700">
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <v-icon icon="fas fa-list-check" start />
          <h1 class="text-headline-sm">
            {{ $t('reflection.open') }}
          </h1>
          <DialogCloseButton class="ms-auto" @click="showDialog = false" />
        </v-card-title>
      </v-card-item>
      <v-card-text>
        {{ t('reflection.selectCompetencesDescription') }}
        <v-checkbox v-for="comp in competences"
                    :key="comp.competence_code" 
                    v-model="selectedCompetences"
                    :disabled="selectedCompetences.length >= 3 && !selectedCompetences.includes(comp.competence_code)"
                    :label="comp.name[locale]"
                    :value="comp.competence_code" />
        <span v-if="selectedCompetences.length > 0">
          {{ t('reflection.reflectionSelectedCompetences', {count: selectedCompetences.length}) }}
        </span>
        <v-banner v-if="disableReflection" class="my-4">
          <template #prepend>
            <v-icon icon="fas fa-warning" />
          </template>
          {{ t('reflection.selectAtLeastOneCompetence') }}
        </v-banner>
      </v-card-text>
      <v-card-actions class="d-flex flex-row align-center justify-around">
        <v-btn class="mt-2"
               color="primary"
               @click="closeDialog">
          {{ $t('closeButton') }}
        </v-btn>
        <v-btn class="mt-2"
               color="primary"
               :disabled="disableReflection"
               @click="startReflection">
          {{ t('reflection.open') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped lang="scss">

</style>
