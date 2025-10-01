import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { addUser, editUser, getUsers, removeUser, resetDeletedIds } from '../features/users/usersSlice'
import { User } from '../features/users/usersTypes'
import type { UsersState } from '../features/users/usersSlice'
import Box from '@mui/material/Box'
import Grid from '@mui/material/Grid'
import Card from '@mui/material/Card'
import CardActions from '@mui/material/CardActions'
import CardContent from '@mui/material/CardContent'
import CardMedia from '@mui/material/CardMedia'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import TextField from '@mui/material/TextField'
import Stack from '@mui/material/Stack'
import PhoneIcon from '@mui/icons-material/Phone'
import EmailIcon from '@mui/icons-material/Email'
import Modal from '@mui/material/Modal'
import Alert from '@mui/material/Alert'
import Snackbar from '@mui/material/Snackbar'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogActions from '@mui/material/DialogActions'
import RefreshIcon from '@mui/icons-material/Refresh'
import AddIcon from '@mui/icons-material/Add'

export default function UsersPage() {
  const dispatch = useAppDispatch()
  const usersState = useAppSelector(state => state.users) as UsersState
  const { items, loading, error } = usersState
  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [editForm, setEditForm] = useState<Partial<User>>({})
  const [alertOpen, setAlertOpen] = useState(false)
  const [alertMessage, setAlertMessage] = useState('')
  const [alertSeverity, setAlertSeverity] = useState<'success' | 'error' | 'warning' | 'info'>('success')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [userToDelete, setUserToDelete] = useState<User | null>(null)
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [addForm, setAddForm] = useState<Partial<User>>({})

  const showAlert = (message: string, severity: 'success' | 'error' | 'warning' | 'info') => {
    setAlertMessage(message)
    setAlertSeverity(severity)
    setAlertOpen(true)
  }

  const handleAlertClose = () => {
    setAlertOpen(false)
  }

  const handleDeleteClick = (user: User) => {
    setUserToDelete(user)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!userToDelete) return
    
    setDeleteDialogOpen(false)
    console.log('Silme işlemi başlatılıyor:', userToDelete.id)
    try {
      const result = await dispatch(removeUser(userToDelete.id))
      if (removeUser.fulfilled.match(result)) {
        showAlert(`${userToDelete.name} kullanıcısı başarıyla silindi!`, 'success')
      } else {
        showAlert('Kullanıcı silinirken bir hata oluştu.', 'error')
      }
    } catch (error) {
      showAlert('Kullanıcı silinirken bir hata oluştu.', 'error')
    }
    setUserToDelete(null)
  }

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false)
    setUserToDelete(null)
  }

  const handleRefresh = () => {
    // Silinen ID'leri temizle
    dispatch(resetDeletedIds())
    // API'den verileri yeniden çek
    dispatch(getUsers())
    showAlert('Kullanıcı listesi yenilendi!', 'success')
  }

  const onAdd = () => {
    setAddForm({
      name: '',
      username: '',
      email: '',
      phone: '',
      website: '',
      address: {
        street: '',
        suite: '',
        city: '',
        zipcode: '',
        geo: { lat: '', lng: '' }
      },
      company: {
        name: '',
        catchPhrase: '',
        bs: ''
      }
    })
    setAddModalOpen(true)
  }

  const handleAddModalClose = () => {
    setAddModalOpen(false)
    setAddForm({})
  }

  const handleAddSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (addForm.name && addForm.email && addForm.username) {
      dispatch(addUser(addForm))
      handleAddModalClose()
      showAlert('Kullanıcı başarıyla eklendi!', 'success')
    }
  }

  useEffect(() => {
    dispatch(getUsers())
  }, [dispatch])

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!addForm.name || !addForm.email) return
    dispatch(addUser(addForm))
    setAddForm({ name: '', email: '', username: '' })
  }

  const onEdit = (user: User) => {
    setEditingUser(user)
    setEditForm({
      name: user.name,
      username: user.username,
      email: user.email,
      phone: user.phone,
      website: user.website,
      address: user.address,
      company: user.company
    })
    setModalOpen(true)
  }

  const handleModalClose = () => {
    setModalOpen(false)
    setEditingUser(null)
    setEditForm({})
  }

  const handleEditSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (editingUser && editForm.name && editForm.email) {
      try {
        const result = await dispatch(editUser({ id: editingUser.id, changes: editForm }))
        if (editUser.fulfilled.match(result)) {
          showAlert(`${editingUser.name} kullanıcısı başarıyla güncellendi!`, 'success')
        } else {
          showAlert('Kullanıcı güncellenirken bir hata oluştu.', 'error')
        }
      } catch (error) {
        showAlert('Kullanıcı güncellenirken bir hata oluştu.', 'error')
      }
      handleModalClose()
    }
  }

  return (
    <div>
      <section>
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', mb: 2 }}>
          <Stack direction="row" spacing={2}>
            <Button 
              variant="contained" 
              startIcon={<AddIcon />} 
              onClick={onAdd}
            >
              Ekle
            </Button>
            <Button 
              variant="outlined" 
              startIcon={<RefreshIcon />} 
              onClick={handleRefresh}
              disabled={loading}
            >
              Yenile
            </Button>
          </Stack>
        </Box>
        <Box sx={{ width: '100%' }}>
          <Grid container spacing={3} alignItems="stretch" justifyContent="center">
            {items.map((u: User) => (
              <Grid component="div" item key={u.id} xs={12} sm={6} md={3} sx={{ display: 'flex', maxWidth: '280px' }}>
                <Card sx={{ 
                  width: '100%', 
                  minWidth: '280px',
                  maxWidth: '280px',
                  display: 'flex', 
                  flexDirection: 'column',
                  backgroundColor: '#ffffff',
                  transition: 'all 0.3s ease-in-out',
                  '&:hover': {
                    transform: 'translateY(-8px)',
                    boxShadow: '0 8px 25px rgba(0,0,0,0.15)',
                    scale: '1.02',
                    backgroundColor: '#f8f9fa'
                  }
                }}>
                  <CardMedia
                    component="img"
                    height="140"
                    image={`https://api.dicebear.com/9.x/initials/svg?seed=${encodeURIComponent(u.name)}&backgroundColor=87ceeb&textColor=ffffff`}
                    alt={u.name}
                  />
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Typography variant="h6" sx={{ fontWeight: 700, color: 'text.primary', mb: 1 }}>
                      {u.name}
                    </Typography>
                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                      <PhoneIcon fontSize="small" color="action" />
                      <Typography variant="body2" color="text.secondary">{u.phone}</Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <EmailIcon fontSize="small" color="action" />
                      <Typography variant="body2" color="text.secondary">{u.email}</Typography>
                    </Stack>
                  </CardContent>
                  <CardActions>
                    <Button size="small" component={Link} to={`/users/${u.id}`}>Detay</Button>
                        <Button size="small" onClick={() => onEdit(u)}>Düzenle</Button>
                    <Button size="small" color="error" onClick={() => handleDeleteClick(u)}>Sil</Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      </section>

      {/* Edit Modal */}
      <Modal
        open={modalOpen}
        onClose={handleModalClose}
        aria-labelledby="modal-modal-title"
        aria-describedby="modal-modal-description"
      >
        <Box sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 600,
          maxHeight: '90vh',
          overflow: 'auto',
          bgcolor: 'background.paper',
          border: '2px solid #000',
          boxShadow: 24,
          p: 4,
        }}>
          <Typography id="modal-modal-title" variant="h6" component="h2" sx={{ mb: 3 }}>
            Kullanıcı Düzenle
          </Typography>
          <form onSubmit={handleEditSubmit}>
            <Stack spacing={2}>
              {/* Temel Bilgiler */}
              <Typography variant="h6" sx={{ mt: 2, mb: 1, color: 'primary.main' }}>
                Temel Bilgiler
              </Typography>
              <TextField
                fullWidth
                label="İsim"
                value={editForm.name || ''}
                onChange={(e) => setEditForm(f => ({ ...f, name: e.target.value }))}
                required
              />
              <TextField
                fullWidth
                label="Kullanıcı Adı"
                value={editForm.username || ''}
                onChange={(e) => setEditForm(f => ({ ...f, username: e.target.value }))}
                required
              />
              <TextField
                fullWidth
                label="Email"
                type="email"
                value={editForm.email || ''}
                onChange={(e) => setEditForm(f => ({ ...f, email: e.target.value }))}
                required
              />
              <TextField
                fullWidth
                label="Telefon"
                value={editForm.phone || ''}
                onChange={(e) => setEditForm(f => ({ ...f, phone: e.target.value }))}
              />
              <TextField
                fullWidth
                label="Website"
                value={editForm.website || ''}
                onChange={(e) => setEditForm(f => ({ ...f, website: e.target.value }))}
              />

              {/* Adres Bilgileri */}
              <Typography variant="h6" sx={{ mt: 3, mb: 1, color: 'primary.main' }}>
                Adres Bilgileri
              </Typography>
              <TextField
                fullWidth
                label="Sokak"
                value={editForm.address?.street || ''}
                onChange={(e) => setEditForm(f => ({ 
                  ...f, 
                  address: { 
                    street: e.target.value,
                    suite: f.address?.suite || '',
                    city: f.address?.city || '',
                    zipcode: f.address?.zipcode || '',
                    geo: f.address?.geo || { lat: '', lng: '' }
                  } 
                }))}
              />
              <TextField
                fullWidth
                label="Suite"
                value={editForm.address?.suite || ''}
                onChange={(e) => setEditForm(f => ({ 
                  ...f, 
                  address: { 
                    street: f.address?.street || '',
                    suite: e.target.value,
                    city: f.address?.city || '',
                    zipcode: f.address?.zipcode || '',
                    geo: f.address?.geo || { lat: '', lng: '' }
                  } 
                }))}
              />
              <TextField
                fullWidth
                label="Şehir"
                value={editForm.address?.city || ''}
                onChange={(e) => setEditForm(f => ({ 
                  ...f, 
                  address: { 
                    street: f.address?.street || '',
                    suite: f.address?.suite || '',
                    city: e.target.value,
                    zipcode: f.address?.zipcode || '',
                    geo: f.address?.geo || { lat: '', lng: '' }
                  } 
                }))}
              />
              <TextField
                fullWidth
                label="Posta Kodu"
                value={editForm.address?.zipcode || ''}
                onChange={(e) => setEditForm(f => ({ 
                  ...f, 
                  address: { 
                    street: f.address?.street || '',
                    suite: f.address?.suite || '',
                    city: f.address?.city || '',
                    zipcode: e.target.value,
                    geo: f.address?.geo || { lat: '', lng: '' }
                  } 
                }))}
              />
              <Stack direction="row" spacing={2}>
                <TextField
                  fullWidth
                  label="Enlem (Lat)"
                  value={editForm.address?.geo?.lat || ''}
                  onChange={(e) => setEditForm(f => ({ 
                    ...f, 
                    address: { 
                      street: f.address?.street || '',
                      suite: f.address?.suite || '',
                      city: f.address?.city || '',
                      zipcode: f.address?.zipcode || '',
                      geo: { 
                        lat: e.target.value,
                        lng: f.address?.geo?.lng || ''
                      } 
                    } 
                  }))}
                />
                <TextField
                  fullWidth
                  label="Boylam (Lng)"
                  value={editForm.address?.geo?.lng || ''}
                  onChange={(e) => setEditForm(f => ({ 
                    ...f, 
                    address: { 
                      street: f.address?.street || '',
                      suite: f.address?.suite || '',
                      city: f.address?.city || '',
                      zipcode: f.address?.zipcode || '',
                      geo: { 
                        lat: f.address?.geo?.lat || '',
                        lng: e.target.value
                      } 
                    } 
                  }))}
                />
              </Stack>

              {/* Şirket Bilgileri */}
              <Typography variant="h6" sx={{ mt: 3, mb: 1, color: 'primary.main' }}>
                Şirket Bilgileri
              </Typography>
              <TextField
                fullWidth
                label="Şirket Adı"
                value={editForm.company?.name || ''}
                onChange={(e) => setEditForm(f => ({ 
                  ...f, 
                  company: { 
                    name: e.target.value,
                    catchPhrase: f.company?.catchPhrase || '',
                    bs: f.company?.bs || ''
                  } 
                }))}
              />
              <TextField
                fullWidth
                label="Slogan"
                value={editForm.company?.catchPhrase || ''}
                onChange={(e) => setEditForm(f => ({ 
                  ...f, 
                  company: { 
                    name: f.company?.name || '',
                    catchPhrase: e.target.value,
                    bs: f.company?.bs || ''
                  } 
                }))}
              />
              <TextField
                fullWidth
                label="İş Tanımı"
                value={editForm.company?.bs || ''}
                onChange={(e) => setEditForm(f => ({ 
                  ...f, 
                  company: { 
                    name: f.company?.name || '',
                    catchPhrase: f.company?.catchPhrase || '',
                    bs: e.target.value
                  } 
                }))}
              />

              <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
                <Button type="submit" variant="contained" color="primary">
                  Güncelle
                </Button>
                <Button variant="outlined" onClick={handleModalClose}>
                  İptal
                </Button>
              </Stack>
            </Stack>
          </form>
        </Box>
      </Modal>

      {/* Add User Modal */}
      <Modal
        open={addModalOpen}
        onClose={handleAddModalClose}
        aria-labelledby="add-modal-title"
        aria-describedby="add-modal-description"
      >
        <Box sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 600,
          maxHeight: '90vh',
          overflow: 'auto',
          bgcolor: 'background.paper',
          border: '2px solid #000',
          boxShadow: 24,
          p: 4,
        }}>
          <Typography id="add-modal-title" variant="h6" component="h2" sx={{ mb: 3 }}>
            Yeni Kullanıcı Ekle
          </Typography>
          <form onSubmit={handleAddSubmit}>
            <Stack spacing={2}>
              {/* Temel Bilgiler */}
              <Typography variant="h6" sx={{ mt: 2, mb: 1, color: 'primary.main' }}>
                Temel Bilgiler
              </Typography>
              <TextField
                fullWidth
                label="İsim"
                value={addForm.name || ''}
                onChange={(e) => setAddForm(f => ({ ...f, name: e.target.value }))}
                required
              />
              <TextField
                fullWidth
                label="Kullanıcı Adı"
                value={addForm.username || ''}
                onChange={(e) => setAddForm(f => ({ ...f, username: e.target.value }))}
                required
              />
              <TextField
                fullWidth
                label="Email"
                type="email"
                value={addForm.email || ''}
                onChange={(e) => setAddForm(f => ({ ...f, email: e.target.value }))}
                required
              />
              <TextField
                fullWidth
                label="Telefon"
                value={addForm.phone || ''}
                onChange={(e) => setAddForm(f => ({ ...f, phone: e.target.value }))}
              />
              <TextField
                fullWidth
                label="Website"
                value={addForm.website || ''}
                onChange={(e) => setAddForm(f => ({ ...f, website: e.target.value }))}
              />

              {/* Adres Bilgileri */}
              <Typography variant="h6" sx={{ mt: 3, mb: 1, color: 'primary.main' }}>
                Adres Bilgileri
              </Typography>
              <TextField
                fullWidth
                label="Sokak"
                value={addForm.address?.street || ''}
                onChange={(e) => setAddForm(f => ({ 
                  ...f, 
                  address: { 
                    street: e.target.value,
                    suite: f.address?.suite || '',
                    city: f.address?.city || '',
                    zipcode: f.address?.zipcode || '',
                    geo: f.address?.geo || { lat: '', lng: '' }
                  } 
                }))}
              />
              <TextField
                fullWidth
                label="Suite"
                value={addForm.address?.suite || ''}
                onChange={(e) => setAddForm(f => ({ 
                  ...f, 
                  address: { 
                    street: f.address?.street || '',
                    suite: e.target.value,
                    city: f.address?.city || '',
                    zipcode: f.address?.zipcode || '',
                    geo: f.address?.geo || { lat: '', lng: '' }
                  } 
                }))}
              />
              <TextField
                fullWidth
                label="Şehir"
                value={addForm.address?.city || ''}
                onChange={(e) => setAddForm(f => ({ 
                  ...f, 
                  address: { 
                    street: f.address?.street || '',
                    suite: f.address?.suite || '',
                    city: e.target.value,
                    zipcode: f.address?.zipcode || '',
                    geo: f.address?.geo || { lat: '', lng: '' }
                  } 
                }))}
              />
              <TextField
                fullWidth
                label="Posta Kodu"
                value={addForm.address?.zipcode || ''}
                onChange={(e) => setAddForm(f => ({ 
                  ...f, 
                  address: { 
                    street: f.address?.street || '',
                    suite: f.address?.suite || '',
                    city: f.address?.city || '',
                    zipcode: e.target.value,
                    geo: f.address?.geo || { lat: '', lng: '' }
                  } 
                }))}
              />
              <Stack direction="row" spacing={2}>
                <TextField
                  fullWidth
                  label="Enlem (Lat)"
                  value={addForm.address?.geo?.lat || ''}
                  onChange={(e) => setAddForm(f => ({ 
                    ...f, 
                    address: { 
                      street: f.address?.street || '',
                      suite: f.address?.suite || '',
                      city: f.address?.city || '',
                      zipcode: f.address?.zipcode || '',
                      geo: { 
                        lat: e.target.value,
                        lng: f.address?.geo?.lng || ''
                      } 
                    } 
                  }))}
                />
                <TextField
                  fullWidth
                  label="Boylam (Lng)"
                  value={addForm.address?.geo?.lng || ''}
                  onChange={(e) => setAddForm(f => ({ 
                    ...f, 
                    address: { 
                      street: f.address?.street || '',
                      suite: f.address?.suite || '',
                      city: f.address?.city || '',
                      zipcode: f.address?.zipcode || '',
                      geo: { 
                        lat: f.address?.geo?.lat || '',
                        lng: e.target.value
                      } 
                    } 
                  }))}
                />
              </Stack>

              {/* Şirket Bilgileri */}
              <Typography variant="h6" sx={{ mt: 3, mb: 1, color: 'primary.main' }}>
                Şirket Bilgileri
              </Typography>
              <TextField
                fullWidth
                label="Şirket Adı"
                value={addForm.company?.name || ''}
                onChange={(e) => setAddForm(f => ({ 
                  ...f, 
                  company: { 
                    name: e.target.value,
                    catchPhrase: f.company?.catchPhrase || '',
                    bs: f.company?.bs || ''
                  } 
                }))}
              />
              <TextField
                fullWidth
                label="Slogan"
                value={addForm.company?.catchPhrase || ''}
                onChange={(e) => setAddForm(f => ({ 
                  ...f, 
                  company: { 
                    name: f.company?.name || '',
                    catchPhrase: e.target.value,
                    bs: f.company?.bs || ''
                  } 
                }))}
              />
              <TextField
                fullWidth
                label="İş Tanımı"
                value={addForm.company?.bs || ''}
                onChange={(e) => setAddForm(f => ({ 
                  ...f, 
                  company: { 
                    name: f.company?.name || '',
                    catchPhrase: f.company?.catchPhrase || '',
                    bs: e.target.value
                  } 
                }))}
              />

              <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
                <Button type="submit" variant="contained" color="primary">
                  Ekle
                </Button>
                <Button variant="outlined" onClick={handleAddModalClose}>
                  İptal
                </Button>
              </Stack>
            </Stack>
          </form>
        </Box>
      </Modal>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-description"
      >
        <DialogTitle id="delete-dialog-title">
          Kullanıcıyı Sil
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="delete-dialog-description">
            {userToDelete?.name} kullanıcısını silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel} color="primary">
            İptal
          </Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Sil
          </Button>
        </DialogActions>
      </Dialog>

      {/* Alert Snackbar */}
      <Snackbar
        open={alertOpen}
        autoHideDuration={4000}
        onClose={handleAlertClose}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert onClose={handleAlertClose} severity={alertSeverity} sx={{ width: '100%' }}>
          {alertMessage}
        </Alert>
      </Snackbar>
    </div>
  )
}
