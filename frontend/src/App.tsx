import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Home } from './pages/Home'
import { MembersList } from './pages/MembersList'
import { MemberDetail } from './pages/MemberDetail'
import { Questions } from './pages/Questions'
import { Patterns } from './pages/Patterns'
import { Graph } from './pages/Graph'
import { Display } from './pages/Display'
import { Messages } from './pages/Messages'
import { MobileQuestion } from './pages/MobileQuestion'
import { DataModel } from './pages/DataModel'
import Demo from './pages/Demo'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Full-screen display mode (no header/nav) */}
        <Route path="/display" element={<Display />} />

        {/* Mobile swipe question interface (no header/nav) */}
        <Route path="/mobile" element={<MobileQuestion />} />
        <Route path="/swipe" element={<MobileQuestion />} />

        {/* Demo page (has its own header) */}
        <Route path="/demo" element={<Demo />} />

        {/* Regular app routes with Layout */}
        <Route
          path="*"
          element={
            <Layout>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/members" element={<MembersList />} />
                <Route path="/members/:id" element={<MemberDetail />} />
                <Route path="/questions" element={<Questions />} />
                <Route path="/patterns" element={<Patterns />} />
                <Route path="/graph" element={<Graph />} />
                <Route path="/data-model" element={<DataModel />} />
                <Route path="/messages" element={<Messages />} />
              </Routes>
            </Layout>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
