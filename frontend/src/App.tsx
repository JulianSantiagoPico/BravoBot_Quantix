import UniversityPage from './components/UniversityPage'
import ChatWidget from './components/ChatWidget'

export default function App() {
  return (
    <>
      {/* Static clone of the university homepage */}
      <UniversityPage />

      {/* Floating chat widget (replaces WhatsApp button) */}
      <ChatWidget />
    </>
  )
}
