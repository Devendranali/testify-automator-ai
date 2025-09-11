import logo from './logo.svg';
import './css/App.css';
import '@fortawesome/fontawesome-free/css/all.min.css';
import 'react-toastify/dist/ReactToastify.css';


import { BrowserRouter , Route , Routes } from 'react-router-dom';

import Home from './components/home';
import Input from './components/inputs';


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path='/' element = { <Home/> } />
        <Route path='/input' element = { <Input/> } />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
