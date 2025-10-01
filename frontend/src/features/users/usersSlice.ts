import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit'
import { createUser, deleteUser, fetchUsers, updateUser } from './usersAPI'
import type { User } from './usersTypes'

export type UsersState = {
  items: User[]
  loading: boolean
  error: string | null
  deletedIds: number[] // Silinen kullanıcı ID'lerini takip et
}

// localStorage'dan silinen ID'leri yükle
const getDeletedIdsFromStorage = (): number[] => {
  try {
    const stored = localStorage.getItem('deletedUserIds')
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

const initialState: UsersState = {
  items: [],
  loading: false,
  error: null,
  deletedIds: getDeletedIdsFromStorage(),
}

async function retry<T>(fn: () => Promise<T>, attempts = 2, delayMs = 500): Promise<T> {
  try {
    return await fn()
  } catch (e) {
    if (attempts <= 0) throw e
    await new Promise(r => setTimeout(r, delayMs))
    return retry(fn, attempts - 1, delayMs * 2)
  }
}

export const getUsers = createAsyncThunk('users/getAll', async () => {
  const data = await retry(() => fetchUsers())
  return data
})

export const addUser = createAsyncThunk(
  'users/add',
  async (payload: Partial<User>, { getState }) => {
    const state = getState() as { users: UsersState }
    const existingUsers = state.users.items
    const data = await createUser(payload, existingUsers)
    return data
  }
)

export const editUser = createAsyncThunk(
  'users/edit',
  async ({ id, changes }: { id: number; changes: Partial<User> }, { getState }) => {
    const state = getState() as { users: UsersState }
    const existingUser = state.users.items.find(u => u.id === id)
    const data = await updateUser(id, changes, existingUser)
    return data
  }
)

export const removeUser = createAsyncThunk('users/remove', async (id: number) => {
  console.log('Redux - removeUser thunk başlatıldı:', id)
  await deleteUser(id)
  console.log('Redux - removeUser thunk tamamlandı:', id)
  return id
})

const usersSlice = createSlice({
  name: 'users',
  initialState,
  reducers: {
    upsertLocal(state, action: PayloadAction<User>) {
      const index = state.items.findIndex(u => u.id === action.payload.id)
      if (index >= 0) state.items[index] = action.payload
      else state.items.unshift(action.payload)
    },
    resetDeletedIds(state) {
      state.deletedIds = []
      localStorage.removeItem('deletedUserIds')
    },
  },
  extraReducers: builder => {
    builder
      .addCase(getUsers.pending, state => {
        state.loading = true
        state.error = null
      })
      .addCase(getUsers.fulfilled, (state, action) => {
        state.loading = false
        // Sadece ilk yüklemede API'den gelen verileri kullan
        // Sonraki güncellemeler Redux store'da tutulur
        if (state.items.length === 0) {
          // İlk yükleme - API'den gelen verileri kullan
          state.items = action.payload.filter(user => !state.deletedIds.includes(user.id))
        } else {
          // Sonraki yüklemeler - sadece yeni kullanıcıları ekle, mevcut güncellemeleri koru
          const apiUsers = action.payload.filter(user => !state.deletedIds.includes(user.id))
          const newUsers = apiUsers.filter(apiUser => 
            !state.items.some(existingUser => existingUser.id === apiUser.id)
          )
          state.items = [...state.items, ...newUsers]
        }
      })
      .addCase(getUsers.rejected, (state, action) => {
        state.loading = false
        state.error = (action.error.message || 'Kullanıcılar alınırken hata oluştu')
      })

      .addCase(addUser.pending, state => {
        state.loading = true
        state.error = null
      })
      .addCase(addUser.fulfilled, (state, action) => {
        state.loading = false
        const exists = state.items.some(u => u.id === action.payload.id)
        if (!exists) state.items.unshift(action.payload)
      })
      .addCase(addUser.rejected, (state, action) => {
        state.loading = false
        state.error = (action.error.message || 'Ekleme sırasında hata oluştu')
      })

      .addCase(editUser.pending, state => {
        state.loading = true
        state.error = null
      })
      .addCase(editUser.fulfilled, (state, action) => {
        state.loading = false
        const idx = state.items.findIndex(u => u.id === action.payload.id)
        if (idx >= 0) state.items[idx] = action.payload
      })
      .addCase(editUser.rejected, (state, action) => {
        state.loading = false
        state.error = (action.error.message || 'Güncelleme sırasında hata oluştu')
      })

      .addCase(removeUser.pending, state => {
        state.loading = true
        state.error = null
      })
      .addCase(removeUser.fulfilled, (state, action) => {
        console.log('Redux - removeUser reducer çalıştı, silinen ID:', action.payload)
        console.log('Redux - Silme öncesi item sayısı:', state.items.length)
        console.log('Redux - Silme öncesi items:', state.items.map(u => u.id))
        state.loading = false
        // Silinen ID'yi deletedIds listesine ekle
        if (!state.deletedIds.includes(action.payload)) {
          state.deletedIds.push(action.payload)
          // localStorage'a kaydet
          localStorage.setItem('deletedUserIds', JSON.stringify(state.deletedIds))
        }
        // Items'dan da kaldır
        state.items = state.items.filter(u => u.id !== action.payload)
        console.log('Redux - Silme sonrası item sayısı:', state.items.length)
        console.log('Redux - Silme sonrası items:', state.items.map(u => u.id))
        console.log('Redux - Silinen ID\'ler:', state.deletedIds)
      })
      .addCase(removeUser.rejected, (state, action) => {
        state.loading = false
        state.error = (action.error.message || 'Silme sırasında hata oluştu')
      })
  },
})

export const { upsertLocal, resetDeletedIds } = usersSlice.actions
export default usersSlice.reducer
