# Conure: Passive Device Artwork Generator, Modelling, and Optimization

Conure is a tool designed to generate inductor artwork and model it using Artificial Neural Networks (ANN) with options for hyperparameter tuning. Our current modeling technique employs ANNs, and the optimization algorithm utilizes NSGA-II. The supported simulator at present is EMX from Cadence.

## Features

- **Artwork Generation**: Easily generate inductor artwork based on provided templates.

<img src="./resources/images/inductorLayout.png" alt="My Image Description" width="600"/>

- **Via Generation**: Easily create vias for different layers with differnt dimensions and spacing, and automatically fill via area with multiple vias. 

<img src="./resources/images/ViaStacking.png" alt="My Image Description" width="300"/>


- **Guard Ring Desing**: Take care of all your guard ring layers with appropriate substrate contacts, and dummuy fill on guard rings. (Currently supports checkered dummmuy filling on guard ring)

<img src="./resources/images/GuardRing.png" alt="My Image Description" width="300"/>
  
  
- **ANN Modelling**: Model inductors using sophisticated artificial neural networks. 

<div style="display: flex;">
    <img src="./resources/images/model_comparision_L.png" alt="Model Comparison L" width="300" style="margin-right: 10px;"/>
    <img src="./resources/images/model_comparision_Q.png" alt="Model Comparison Q" width="300"/>
</div>

  
- **Optimization**: Utilize the NSGA-II algorithm for inductor optimization.

<img src="./resources/images/Pareto.png" alt="My Image Description" width="300"/>

- **EMX Simulation**: Seamlessly simulate using the Cadence EMX simulator.

## Work in Progress

- Support for openEMS.
  
- A graphical user interface (GUI) for more user-friendly interactions.
  
- Additional inductor optimization techniques.
  
- Hot encoding for process technology to be utilized in models.

## Getting Started

Feel free to test out the artwork generator. Example templates for artwork can be found in the `artwork_library` directory.

### Examples

#### Artwork Generation

```bash
$ python artwork_generator/artwork_generator.py -a artwork_library/Inductors/Coplanar/Inductor_Coplanar_5.json -o OUTPUT -n artwork
```

#### EM Simulation

```bash
$ python simulator/simulate.py -f OUTPUT/artwork.gds -c simulator/config.json --sim "emx" -a artwork_library/Inductors/Coplanar/Inductor_Coplanar_5.json -o OUTPUT -n artwork
```

#### Sweep Feature (iterative Artwork Generation with EM Simulation)
```bash
$ python sweep/sweep.py -a artwork_library/Inductors/Coplanar/Inductor_Coplanar_5.json --sweep sweep.json  -o SWEEP_OUTPUT --layout --simulate -c simulator/config.json --sim "emx"
```


