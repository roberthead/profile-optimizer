import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Home } from './pages/Home'
import { MembersList } from './pages/MembersList'
import { MemberDetail } from './pages/MemberDetail'
import { Questions } from './pages/Questions'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/members" element={<MembersList />} />
          <Route path="/members/:id" element={<MemberDetail />} />
          <Route path="/questions" element={<Questions />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
