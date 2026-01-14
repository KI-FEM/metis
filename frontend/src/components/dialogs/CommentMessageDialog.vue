<script setup lang="ts">
  import { ref } from 'vue'
  import { useI18n } from 'vue-i18n'

  import { useChatStore } from '@/stores/chat'
  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue'

  const props = defineProps<{
    /** The ID of the message to comment on */
    messageId: string,
  }>()
  const {t} = useI18n()
  const chatStore = useChatStore()

  const showDialog = defineModel<boolean>({default: false})
  const comment = ref<string>('')
  const vote = ref<number | null>(null)

  function closeDialog() {
    showDialog.value = false
    comment.value = ''
    vote.value = null
  }

  async function saveComment() {
    await chatStore.addComment(props.messageId, comment.value, vote.value)
    closeDialog()
  }
</script>

<template>
  <v-dialog v-model="showDialog" max-width="700">
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <v-icon icon="mdi mdi-creation-outline" start />
          <h1 class="text-headline-sm">
            {{ $t('comment.title') }}
          </h1>
          <DialogCloseButton class="ms-auto" @click="closeDialog" />
        </v-card-title>
      </v-card-item>
      <v-card-text>
        <p>{{ $t('comment.description') }}</p>
        <v-textarea v-model="comment"
                    :label="t('comment.placeholder')"
                    outlined
                    rows="4" />
        <div class="d-flex flex-row align-center justify-center">
          <div class="d-flex flex-column align-center justify-center ga-2">
            {{ $t('comment.voteLabel') }}
            <v-btn-toggle v-model="vote" color="deep-purple-accent-3" variant="tonal">
              <v-btn class="me-2" icon="mdi mdi-thumb-up" value="1" />
              <v-btn icon="mdi mdi-thumb-down" value="0" />
            </v-btn-toggle>
          </div>
        </div>
      </v-card-text>

      <v-card-actions>
        <v-btn color="primary"
               :text="$t('comment.close')"
               variant="outlined"
               @click="closeDialog" />
        <v-btn color="primary"
               :disabled="comment.length==0"
               :text="$t('comment.save')"
               variant="flat"
               @click="saveComment" />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped lang="scss">

</style>