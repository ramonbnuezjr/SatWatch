# SatWatch Skybox - High Resolution Space Background

This folder contains skybox images for the realistic space background in the Cesium viewer.

## Quick Setup (Recommended)

Download the **Tycho-2 Starfield Skybox** (4K resolution, free for non-commercial use):

1. Visit: https://svs.gsfc.nasa.gov/cgi-bin/details.cgi?aid=3895
2. Or use these free astronomical skyboxes:
   - **Stellarium**: https://github.com/Stellarium/stellarium/tree/master/skycultures
   - **Space Engine**: https://spaceengine.org/ (has exportable skyboxes)

## File Naming Convention

Place 6 cube map images in this folder with these exact names:

| File | Face | Description |
|------|------|-------------|
| `px.jpg` | Positive X | Right face |
| `nx.jpg` | Negative X | Left face |
| `py.jpg` | Positive Y | Top face |
| `ny.jpg` | Negative Y | Bottom face |
| `pz.jpg` | Positive Z | Front face |
| `nz.jpg` | Negative Z | Back face |

## Recommended Sources (Free)

### NASA/ESA Deep Space Imagery
- **NASA Visible Earth**: https://visibleearth.nasa.gov/
- **ESO (European Southern Observatory)**: https://www.eso.org/public/images/
- **Hubble Gallery**: https://hubblesite.org/images/gallery

### Pre-made Skyboxes
- **OpenGameArt Space Skyboxes**: https://opengameart.org/content/space-skyboxes-0
- **Poly Haven HDRIs**: https://polyhaven.com/hdris (convert to cube map)

## Image Specifications

For best quality:
- **Resolution**: 2048x2048 or 4096x4096 per face
- **Format**: JPG (smaller file size) or PNG (lossless)
- **Color**: True color (24-bit)
- **Content**: Milky Way, stars, nebulae

## Converting Panoramic Images to Cube Maps

If you have a panoramic/equirectangular image:

1. Use **HDRI to CubeMap**: https://matheowis.github.io/HDRI-to-CubeMap/
2. Or **cmft**: https://github.com/dariomanesku/cmft
3. Or Blender (free): Import as environment texture, render cube faces

## Testing

After adding images, refresh the Cesium viewer. The console will show:
- `Local skybox loaded` - Success!
- `Custom skybox failed` - Check file names and paths

## Fallback

If no skybox images are found, the viewer will use:
1. A remote Milky Way texture (requires internet)
2. The default Cesium skybox (lower quality)
