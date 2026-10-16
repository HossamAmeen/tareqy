import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '../api/requests'

export const useRequestsStore = defineStore('requests', () => {
  const items = ref<api.TripRequest[]>([])
  const areas = ref<api.Area[]>([])

  async function loadAreas() {
    if (!areas.value.length) areas.value = await api.fetchAreas()
    return areas.value
  }

  async function load() {
    items.value = await api.fetchRequests()
  }

  function upsert(request: api.TripRequest) {
    const index = items.value.findIndex((r) => r.id === request.id)
    if (index >= 0) items.value[index] = request
    else items.value.unshift(request)
    return request
  }

  const create = async (payload: api.RequestPayload) => upsert(await api.createRequest(payload))
  const update = async (id: number, payload: Partial<api.RequestPayload>) =>
    upsert(await api.updateRequest(id, payload))
  const cancel = async (id: number) => upsert(await api.cancelRequest(id))
  // Always trust the server state: a fetched request replaces any cached copy.
  const refresh = async (id: number) => upsert(await api.fetchRequest(id))

  return { items, areas, loadAreas, load, create, update, cancel, refresh }
})
