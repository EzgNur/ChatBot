import { Routes, Route, NavLink } from 'react-router-dom'
import UsersPage from './pages/UsersPage'
import UserDetailPage from './pages/UserDetailPage'
import ChatbotComponent from './pages/ChatbotComponent'

export default function App() {
  return (
    <div className="container">
      <header className="header">
        <h1>Kullanıcılar</h1>
        <nav>
          <NavLink to="/" className={({ isActive }) => isActive ? 'link active' : 'link'}>
            Ana Sayfaya Dön
          </NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<UsersPage />} />
          <Route path="/users/:id" element={<UserDetailPage />} />
        </Routes>
      </main>
      
      {/* Chatbot - Her sayfada görünür */}
      <ChatbotComponent />
    </div>
  )
}
