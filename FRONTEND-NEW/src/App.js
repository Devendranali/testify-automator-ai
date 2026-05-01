import './App.css';
import '@fortawesome/fontawesome-free/css/all.min.css';
import 'react-toastify/dist/ReactToastify.css';

import React from "react";
import { BrowserRouter, Route, Routes, Navigate, useLocation } from 'react-router-dom';
import { ToastContainer, toast } from 'react-toastify';

import Home from './components/home';
import Input from './components/inputs';
import Login from './components/login';
import Signup from './components/signup';
import TestRunner from './components/testrunner';
import Prompts from './components/prompts';
import { setToastScope } from "./utils/scopedToast";



const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('token');
  return token ? children : <Navigate to="/login" />;
};

const ToastScopeSync = () => {
  const location = useLocation();
  const scope = location.pathname;
  setToastScope(scope);

  React.useEffect(() => {
    toast.dismiss();
  }, [scope]);

  return null;
};

function App() {
  return (
    <BrowserRouter>
      <ToastScopeSync />
      <Routes>
        <Route path='/login' element={<Login />} />
        <Route path='/signup' element={<Signup />} />
        
        <Route
          path='/'
          element={
            <ProtectedRoute>
              <Home />
            </ProtectedRoute>
          }
        />
        <Route
          path='/editor'
          element={
            <ProtectedRoute>
              <Home editorOnly />
            </ProtectedRoute>
          }
        />
        <Route
          path='/input'
          element={
            <ProtectedRoute>
              <Input />
            </ProtectedRoute>
          }
        />
        <Route
          path='/input/upload'
          element={
            <ProtectedRoute>
              <Input />
            </ProtectedRoute>
          }
        />
        <Route
          path='/input/image-update'
          element={
            <ProtectedRoute>
              <Input />
            </ProtectedRoute>
          }
        />
        <Route
          path='/input/story'
          element={
            <ProtectedRoute>
              <Input />
            </ProtectedRoute>
          }
        />
        <Route
          path='/input/url'
          element={
            <ProtectedRoute>
              <Input />
            </ProtectedRoute>
          }
        />
        <Route
          path='/input/execute'
          element={
            <ProtectedRoute>
              <Input />
            </ProtectedRoute>
          }
        />
        <Route
            path='/test-runner'
            element={
              <ProtectedRoute>
                <TestRunner />
              </ProtectedRoute>
            }
          />
          <Route
            path='/prompts'
            element={
              <ProtectedRoute>
                <Prompts />
              </ProtectedRoute>
            }
          />  

      </Routes>
      <ToastContainer position="top-right" autoClose={4000} newestOnTop closeOnClick pauseOnHover draggable theme="colored" />
    </BrowserRouter>
  );
}

export default App;
