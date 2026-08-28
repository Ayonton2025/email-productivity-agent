import React from 'react';
import { AuthProvider as ContextAuthProvider } from '../context/AuthContext';

const AuthProvider = ({ children }) => <ContextAuthProvider>{children}</ContextAuthProvider>;

export default AuthProvider;
