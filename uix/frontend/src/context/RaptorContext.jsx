import { createContext, useContext, useState } from 'react';

const RaptorContext = createContext();

export const RaptorProvider = ({ children }) => {
  // Add state here as needed
  const [raptorConfig, setRaptorConfig] = useState({});

  return (
    <RaptorContext.Provider value={{ raptorConfig, setRaptorConfig }}>
      {children}
    </RaptorContext.Provider>
  );
};

export const useRaptorContext = () => useContext(RaptorContext);
