import { useMemo, useState, FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { editUser, removeUser } from '../features/users/usersSlice'
import { User } from '../features/users/usersTypes'
import Box from '@mui/material/Box'
import Container from '@mui/material/Container'
import Typography from '@mui/material/Typography'
import Avatar from '@mui/material/Avatar'
import Stack from '@mui/material/Stack'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Button from '@mui/material/Button'
import Divider from '@mui/material/Divider'
import Grid from '@mui/material/Grid'
import Paper from '@mui/material/Paper'
import Skeleton from '@mui/material/Skeleton'
import Modal from '@mui/material/Modal'
import TextField from '@mui/material/TextField'
import Alert from '@mui/material/Alert'
import Snackbar from '@mui/material/Snackbar'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogActions from '@mui/material/DialogActions'
import PhoneIcon from '@mui/icons-material/Phone'
import EmailIcon from '@mui/icons-material/Email'
import LanguageIcon from '@mui/icons-material/Language'
import LocationOnIcon from '@mui/icons-material/LocationOn'
import BusinessIcon from '@mui/icons-material/Business'
import PersonIcon from '@mui/icons-material/Person'
import EditIcon from '@mui/icons-material/Edit'

export default function UserDetailPage() {
  const { id } = useParams()
  const userId = Number(id)
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const users = useAppSelector(s => s.users.items)
  const user = useMemo(() => users.find(u => u.id === userId), [users, userId])
  
  const [modalOpen, setModalOpen] = useState(false)
  const [editForm, setEditForm] = useState<Partial<User>>({})
  const [alertOpen, setAlertOpen] = useState(false)
  const [alertMessage, setAlertMessage] = useState('')
  const [alertSeverity, setAlertSeverity] = useState<'success' | 'error' | 'warning' | 'info'>('success')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  const showAlert = (message: string, severity: 'success' | 'error' | 'warning' | 'info') => {
    setAlertMessage(message)
    setAlertSeverity(severity)
    setAlertOpen(true)
  }

  const handleAlertClose = () => {
    setAlertOpen(false)
  }

  if (!user) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="h4" color="error">
            Kullanıcı Bulunamadı
          </Typography>
          <Button variant="contained" onClick={() => navigate('/')} sx={{ mt: 2 }}>
            Ana Sayfaya Dön
          </Button>
        </Box>
        
        {/* Alert Snackbar for user not found */}
        <Snackbar
          open={true}
          autoHideDuration={4000}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        >
          <Alert severity="error" sx={{ width: '100%' }}>
            Kullanıcı bulunamadı! Ana sayfaya yönlendiriliyorsunuz.
          </Alert>
        </Snackbar>
      </Container>
    )
  }

  const onDelete = () => {
    if (!user) return
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!user) return
    
    setDeleteDialogOpen(false)
    console.log('UserDetailPage - Silme işlemi başlatılıyor:', userId)
    try {
      const result = await dispatch(removeUser(userId))
      console.log('UserDetailPage - Silme işlemi sonucu:', result)
      if (removeUser.fulfilled.match(result)) {
        console.log('UserDetailPage - Silme başarılı')
        showAlert(`${user.name} kullanıcısı başarıyla silindi!`, 'success')
        // Alert'in görünmesi için bekle, sonra yönlendir
        setTimeout(() => {
          navigate('/', { replace: true })
        }, 2000) // 2 saniye sonra ana sayfaya yönlendir
      } else {
        console.log('UserDetailPage - Silme başarısız:', result.error)
        showAlert('Kullanıcı silinirken bir hata oluştu.', 'error')
      }
    } catch (error) {
      console.error('UserDetailPage - Silme işlemi hatası:', error)
      showAlert('Kullanıcı silinirken bir hata oluştu.', 'error')
    }
  }

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false)
  }

  const onEdit = () => {
    if (user) {
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
  }

  const handleModalClose = () => {
    setModalOpen(false)
    setEditForm({})
  }

  const handleEditSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (editForm.name && editForm.email) {
      try {
        const result = await dispatch(editUser({ id: userId, changes: editForm }))
        if (editUser.fulfilled.match(result)) {
          showAlert(`${user?.name} kullanıcısı başarıyla güncellendi!`, 'success')
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
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      {/* Header Section */}
      <Paper elevation={3} sx={{ p: 4, mb: 3, borderRadius: 2 }}>
        <Stack direction="row" spacing={3} alignItems="flex-start">
          <Avatar
            sx={{
              width: 80,
              height: 80,
              bgcolor: '#87ceeb',
              fontSize: '2rem',
              fontWeight: 'bold'
            }}
            src={`https://api.dicebear.com/9.x/initials/svg?seed=${encodeURIComponent(user.name)}&backgroundColor=87ceeb&textColor=ffffff`}
          >
            {user.name.split(' ').map(n => n[0]).join('')}
          </Avatar>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h3" component="h1" sx={{ fontWeight: 'bold', mb: 1 }}>
              {user.name}
            </Typography>
            <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
              @{user.username}
            </Typography>
            <Stack direction="row" spacing={2}>
              <Button variant="contained" startIcon={<EditIcon />} onClick={onEdit}>
                Düzenle
              </Button>
              <Button variant="contained" color="error" onClick={onDelete}>
                Kullanıcıyı Sil
              </Button>
            </Stack>
          </Box>
        </Stack>
      </Paper>

      {/* Contact Information */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h5" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
            <PersonIcon sx={{ mr: 1 }} />
            İletişim Bilgileri
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Grid container spacing={2}>
            <Grid columns={{xs:12, sm:6}}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <EmailIcon color="primary" />
                <Typography variant="body1">
                  <strong>Email:</strong> {user.email}
                </Typography>
              </Stack>
            </Grid>
            <Grid columns={{xs:12, sm:6}}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <PhoneIcon color="primary" />
                <Typography variant="body1">
                  <strong>Telefon:</strong> {user.phone}
                </Typography>
              </Stack>
            </Grid>
            <Grid columns={{xs:12}}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <LanguageIcon color="primary" />
                <Typography variant="body1">
                  <strong>Website:</strong> {user.website}
                </Typography>
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Address Information */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h5" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
            <LocationOnIcon sx={{ mr: 1 }} />
            Adres Bilgileri
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Grid container spacing={2}>
            <Grid columns={{xs:12, sm:6}}>
              <Typography variant="body1" sx={{ mb: 1 }}>
                <strong>Sokak:</strong> {user.address.street}
              </Typography>
              <Typography variant="body1" sx={{ mb: 1 }}>
                <strong>Suite:</strong> {user.address.suite}
              </Typography>
            </Grid>
            <Grid columns={{xs:12, sm:6}}>
              <Typography variant="body1" sx={{ mb: 1 }}>
                <strong>Şehir:</strong> {user.address.city}
              </Typography>
              <Typography variant="body1" sx={{ mb: 1 }}>
                <strong>Posta Kodu:</strong> {user.address.zipcode}
              </Typography>
            </Grid>
            <Grid columns={{xs:12}}>
              <Typography variant="body1" sx={{ mb: 1 }}>
                <strong>Koordinatlar:</strong> {user.address.geo.lat}, {user.address.geo.lng}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Company Information */}
      <Card>
        <CardContent>
          <Typography variant="h5" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
            <BusinessIcon sx={{ mr: 1 }} />
            Şirket Bilgileri
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Grid container spacing={2}>
            <Grid columns={{xs:12}}>
              <Typography variant="h6" sx={{ mb: 1 }}>
                {user.company.name}
              </Typography>
              <Typography variant="body1" sx={{ mb: 2, fontStyle: 'italic' }}>
                "{user.company.catchPhrase}"
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {user.company.bs}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

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
            {user?.name} kullanıcısını silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.
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
    </Container>
  )
}
