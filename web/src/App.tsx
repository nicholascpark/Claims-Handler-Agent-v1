import { Header } from './components/Header';
import { ChatInterface } from './components/ChatInterface';

function App() {
  return (
    <div className="min-h-screen bg-white font-sans text-slate-900">
      <Header />
      <main>
        <ChatInterface />
      </main>
    </div>
  );
}

export default App;
