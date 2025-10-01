import axios, { AxiosError } from 'axios'
import type { User } from './usersTypes'

const api = axios.create({
  baseURL: 'https://jsonplaceholder.typicode.com',
  timeout: 8000,
  headers: { 'Accept': 'application/json' },
})

function mapAxiosError(error: unknown): Error {
  if (axios.isAxiosError(error)) {
    const err = error as AxiosError<any>
    if (err.code === 'ECONNABORTED') return new Error('İstek zaman aşımına uğradı (timeout).')
    if (err.response) {
      const status = err.response.status
      const msg = typeof err.response.data === 'string' ? err.response.data : (err.response.data?.message || 'Bilinmeyen sunucu hatası')
      return new Error(`Sunucu hatası (${status}): ${msg}`)
    }
    return new Error('Ağ hatası: Sunucuya ulaşılamadı. İnternet bağlantınızı kontrol edin.')
  }
  return new Error('Beklenmeyen bir hata oluştu')
}

export async function fetchUsers(): Promise<User[]> {
  try {
    const { data } = await api.get<User[]>('/users')
    return data
  } catch (e) {
    throw mapAxiosError(e)
  }
}

export async function createUser(user: Partial<User>, existingUsers: User[] = []): Promise<User> {
  try {
    const { data } = await api.post<User>('/users', user)
    return data
  } catch (e) {
    // JSONPlaceholder API'si oluşturma için 500 hatası döndürebilir
    // Bu durumda yeni kullanıcıyı simüle ediyoruz
    if (axios.isAxiosError(e) && e.response?.status === 500) {
      // Yeni ID oluştur (Redux store'daki mevcut kullanıcıların en büyük ID'si + 1)
      const maxId = existingUsers.length > 0 ? Math.max(...existingUsers.map(u => u.id)) : 0
      const newId = maxId + 1
      
      return {
        id: newId,
        name: user.name || '',
        username: user.username || '',
        email: user.email || '',
        phone: user.phone || '',
        website: user.website || '',
        address: user.address || {
          street: '',
          suite: '',
          city: '',
          zipcode: '',
          geo: { lat: '', lng: '' }
        },
        company: user.company || {
          name: '',
          catchPhrase: '',
          bs: ''
        }
      }
    }
    throw mapAxiosError(e)
  }
}

export async function updateUser(id: number, user: Partial<User>, existingUser?: User): Promise<User> {
  try {
    // JSONPlaceholder API'si güncelleme için 500 hatası döndürür
    // Bu yüzden simüle ediyoruz
    const { data } = await api.put<User>(`/users/${id}`, user)
    return data
  } catch (e) {
    // JSONPlaceholder API'si güncelleme için 500 hatası döndürür
    // Bu durumda güncellenmiş kullanıcıyı simüle ediyoruz
    if (axios.isAxiosError(e) && e.response?.status === 500) {
      // Eğer existingUser parametresi varsa (yeni eklenen kullanıcı), onu kullan
      if (existingUser) {
        return { ...existingUser, ...user, id }
      }
      
      // API'den gelen kullanıcıyı al ve güncellemeleri uygula
      try {
        const { data: apiUser } = await api.get<User>(`/users/${id}`)
        return { ...apiUser, ...user, id }
      } catch (getError) {
        // API'de kullanıcı bulunamadı (404) - bu yeni eklenen kullanıcı olabilir
        if (axios.isAxiosError(getError) && getError.response?.status === 404) {
          throw new Error(`Kullanıcı bulunamadı (ID: ${id}). Bu yeni eklenen bir kullanıcı olabilir.`)
        }
        throw mapAxiosError(getError)
      }
    }
    throw mapAxiosError(e)
  }
}

export async function deleteUser(id: number): Promise<{ id: number }> {
  try {
    await api.delete(`/users/${id}`)
    return { id }
  } catch (e) {
    throw mapAxiosError(e)
  }
}
