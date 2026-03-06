import { createContext, useContext, useState } from 'react';

const OpenEmsContext = createContext();

export const OpenEmsProvider = ({ children }) => {
  // Add state here as needed
  const [openEmsConfig, setOpenEmsConfig] = useState({});

  return (
    <OpenEmsContext.Provider value={{ openEmsConfig, setOpenEmsConfig }}>
      {children}
    </OpenEmsContext.Provider>
  );
};

export const useOpenEmsContext = () => useContext(OpenEmsContext);
