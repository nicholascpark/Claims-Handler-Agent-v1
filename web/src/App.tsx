import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Landing } from './pages/Landing';
import { Builder } from './pages/Builder';
import { Test } from './pages/Test';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/builder" element={<Builder />} />
        <Route path="/builder/:formId" element={<Builder />} />
        <Route path="/test/:formId" element={<Test />} />
      </Routes>
    </Router>
  );
}

export default App;
