# Megafans Observatory

Welcome to the **Megafans Observatory**, an interactive web-based platform dedicated to the exploration and study of the world's megafans. 

## About the Project
This observatory serves as the digital companion and visualizer for the novel global geodatabase of megafans produced in the dissertation: **"Geomorphology of Megafans" (Sounny-Slitine, 2020)**. 

Megafans—large fan-shaped landforms greater than 10³ square-kilometers built by rivers exiting topographic fronts—are some of the least understood landforms on Earth, often popularly referred to as "inland deltas." This site provides an interactive map and catalog to visualize morphometrics of global megafans and their contributing source basins across major regions including the Chaco Plain, the Sahel, Himalayan Forelands, Okavango Delta, and the Pantanal.

## Features
- **Global Map Visualization**: Interactive Leaflet map displaying the locations and spatial footprints of megafans worldwide.
- **Data Catalog**: Browse through the complete dataset of megafans, exploring their unique metrics and distinguishing characteristics.
- **Satellite Imagery Integration**: Direct links and views of megafans using satellite imagery.

## Development

The site is built with React and Tailwind CSS. 

### Local Setup
To run the site locally, you will need a basic web server to bypass CORS restrictions for fetching the local data.
```bash
python -m http.server 8000
```
Then navigate to `http://localhost:8000` in your web browser.

## Citation
If you use data from this observatory, please reference the original dissertation:
*Sounny-Slitine, M. M. A. A. (2020). Geomorphology of Megafans [Ph.D. Dissertation, The University of Texas at Austin].*
