import { onBeforeUnmount, onMounted, ref } from 'vue'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

export function useInstallPrompt() {
  const deferred = ref<BeforeInstallPromptEvent | null>(null)

  const onPrompt = (e: Event) => {
    e.preventDefault()
    deferred.value = e as BeforeInstallPromptEvent
  }

  onMounted(() => window.addEventListener('beforeinstallprompt', onPrompt))
  onBeforeUnmount(() => window.removeEventListener('beforeinstallprompt', onPrompt))

  async function install() {
    if (!deferred.value) return
    await deferred.value.prompt()
    deferred.value = null
  }

  return { canInstall: deferred, install }
}
