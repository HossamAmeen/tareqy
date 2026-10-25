import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '../api/driver'

export const useDriverStore = defineStore('driver', () => {
  const profile = ref<api.DriverProfile | null>(null)
  const requests = ref<api.MatchedRequest[]>([])

  async function loadProfile() {
    profile.value = await api.fetchDriverProfile()
  }

  async function update(payload: api.DriverProfilePayload) {
    profile.value = await api.updateDriverProfile(payload)
  }

  async function reportLocation(latitude: string, longitude: string) {
    profile.value = await api.sendDriverLocation(latitude, longitude)
  }

  // Always trust the server list: closed or expired requests disappear on the next load.
  async function loadRequests() {
    requests.value = await api.fetchMatchingRequests()
  }

  async function setInterest(id: number, interested: boolean) {
    if (interested) await api.expressInterest(id)
    else await api.withdrawInterest(id)
    await loadRequests()
  }

  return { profile, requests, loadProfile, update, reportLocation, loadRequests, setInterest }
})
