<script setup lang="ts">
  import {ref, computed, onMounted} from 'vue'
  import {useI18n} from 'vue-i18n'

  import type {paths} from '@/types_api'

  import {useLearningTypesStore} from '@/stores/learningTypes'

  const {locale} = useI18n()
  const learningTypesStore = useLearningTypesStore()

  const otpInput = ref('')
  const isFetching = ref(false)
  const isError = ref(false)
  const personality = ref('')

  type PersonalityType = paths['/learning_types/from_personality/{personality_type}']['get']['parameters']['path']['personality_type']

  const isValid = computed(() => {
    const validLetters = ['IE', 'NS', 'TF', 'JP']
    return otpInput.value.length <= 4 && [...otpInput.value].every((char, i) => validLetters[i]?.includes(char))
  })

  async function evaluatePersonalityType() {
    personality.value = otpInput.value

    try {
      isError.value = false
      isFetching.value = true
      await learningTypesStore.convertPersonalityType(personality.value as PersonalityType)
      await new Promise(resolve => setTimeout(resolve, 800))
    } catch (error) {
      isError.value = true
    } finally {
      isFetching.value = false
    }
  }

  onMounted(() => {
    const otpInputs = Array.from(document.getElementsByClassName('v-otp-input__field'))
    otpInputs.forEach((otpInput, index) => {
      otpInput.setAttribute('aria-describedby', 'personalityFormError')
      // otpInput.setAttribute('placeholder', ['I', 'N', 'T', 'J'][index])
    })
  })
</script>

<template>
  <v-card class="mt-4 mx-auto pa-6 text-center" variant="outlined" width="fit-content">
    <v-form @submit.prevent="evaluatePersonalityType">
      <strong>{{ $t('learningTypesPersonalityLabel') }}:</strong>
      <v-otp-input :disabled="isFetching"
                   :error="!isValid"
                   length="4"
                   :model-value="otpInput"
                   type="text"
                   @update:model-value="value => otpInput = value.toUpperCase()" />
      <div id="personalityFormError" aria-live="assertive" class="mt-n3 mb-3 text-error">
        {{ isValid ? '' : $t('learningTypesPersonalityInvalid') }}
      </div>
      <v-btn :disabled="!isValid || otpInput.length !== 4"
             :loading="isFetching"
             :text="$t('learningTypesPersonalitySubmit')"
             type="submit"
             variant="tonal" />
    </v-form>
  </v-card>
  <v-alert v-if="isError"
           class="mt-4 text-body-lg"
           color="error-container"
           type="error">
    <I18nT keypath="learningTypesError" scope="global">
      <a href="#" @click.prevent="evaluatePersonalityType">{{ $t('learningTypesTryAgain') }}</a>
    </I18nT>
  </v-alert>
  <v-alert v-else-if="!isFetching && personality"
           class="mt-4 text-body-lg"
           color="surface-variant"
           :text="$t('learningTypesPersonalitySuccess', {personality: personality, learningType: learningTypesStore.selectedLearningType?.title[locale]})"
           type="success" />
</template>

<style scoped lang="scss">
  :deep(.v-otp-input__content) {
    max-width: calc(4 * 64px - 3 * .5rem);
  }
</style>
