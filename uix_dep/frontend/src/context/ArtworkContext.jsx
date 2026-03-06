// ArtworkContext.jsx
import { createContext, useContext, useState } from 'react';

const ArtworkContext = createContext();

export function ArtworkProvider({ children }) {
    // State for layers
    const [layerData, setLayerData] = useState([
        { name: '', gdsLayer: '', gdsDatatype: '' }
    ]);


    // State for Vias
    const [viaData, setViaData] = useState([
        { name: '', length: '', width: '', spacing: '', angle: '', layer: '' }
      ]);

    // State for Via Pad Stack
    const [viaPadStackData, setViaPadStackData] = useState([
        { name: '', topLayer: '', bottomLayer: '', margin: '', viaList: '' }
    ]);

    // State for Bridges
    const [bridgeData, setBridgeData] = useState([
        { name: '', layer: '', viaStackCCW: '' , viaStackCW: ''}
        // { name: '', layer: '', via: '', viaWidth: '', viaStackCCW: '' , viaStackCW: ''}
    ]);


    // State for Ports
    const [portData, setPortData] = useState([
        { name: '', label: ''}
    ]);

    // State for Simulation Ports
    const [simPortData, setSimPortData] = useState([
        { portId: '', portType: '', plusPort: '', minusPort: '', enable: ''}
    ]);

    // State for Simulation Ports
    const [armData, setArmData] = useState([
        { name: '', type: '', length: '', width: '', spacing: '', port1: '', port2: '', layer: '', viaPadStack: ''}
    ]);

    // State for segments
    const [segmentData, setSegmentData] = useState(
        Array(8).fill().map(() => ([
            { type: '', item: '', layer: '', jump: '' }
        ])) // 8 empty arrays = 8 segments
    );


    // State for Parameters
    const [parameterData, setParameterData] = useState([
        { parameter: '', value: '' }
    ]);
    
    
    // State for Metadata
    const [metaData, setMetaData] = useState([
        { parameter: '', value: '' }
    ]);
    


    // New global-level state for guard ring settings
    const [useGuardRing, setUseGuardRing] = useState(false);
    const [guardRingDistance, setGuardRingDistance] = useState('');

    // State for Guard Ring
    const [guardRingData, setGuardRingData] = useState([
        { name: '', shape: '', offset: '' , width: '' , layer: '' , 
        contacts: '' , viaPadStack: '' , UsePartialCut: '' , partialCutSegments: '' , spacing: ''  }
    ]);

    // State for Guard Ring Dummy Fillings
    const [guardRingDummyData, setGuardRingDummyData] = useState([
        { name: '', shape: '', length: '' , height: '' , offsetX: '' , 
        offsetY: '' , layers: ''   }
    ]);


    // The combined value that holds both states and their updaters
    // const value = {
    //     layerData,
    //     setLayerData,
    //     segmentData,
    //     setSegmentData,
    // };


    const value = {
        metadata: { metaData, setMetaData },
        parameter: { parameterData, setParameterData },
        layers: { layerData, setLayerData },
        vias: { viaData, setViaData },
        segments: { segmentData, setSegmentData },
        ports: {
          portData, setPortData,
          simPortData, setSimPortData
        },
        arms: { armData, setArmData },
        bridges: { bridgeData, setBridgeData },
        viaPadStack: { viaPadStackData, setViaPadStackData },
        guardRing: {
            useGuardRing, setUseGuardRing,
            guardRingDistance, setGuardRingDistance,
            guardRingData, setGuardRingData,
            guardRingDummyData, setGuardRingDummyData
            
          },
      };

      

    return (
        <ArtworkContext.Provider value={value}>
            {children}
        </ArtworkContext.Provider>
    );
}

export function useArtworkContext() {
    return useContext(ArtworkContext);
}
