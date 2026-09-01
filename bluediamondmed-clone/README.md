# Blue Diamond Medical Staffing — Static Clone

An exact static mirror of [bluediamondmed.com](https://bluediamondmed.com/) (a
WordPress / Elementor site), rebuilt as plain HTML/CSS/JS.

## Pages

| File | Live page |
|------|-----------|
| `index.html` | Home |
| `about-us.html` | About Us |
| `services.html` | Services |
| `healthcare-staffing-services-page.html` | School Staffing |
| `school-staffing.html` | Healthcare Staffing |
| `healthcare-professionals.html` | Healthcare Professionals |
| `teachers-substitute-educators.html` | Teachers & Substitute Educators |
| `cpr-emergency-training-certification.html` | CPR & Emergency Training Certification |
| `teach-in-the-u-s-a-with-blue-diamond-school-staffing.html` | Teach in the U.S.A. |
| `healthcare-staffing.html` | Jobs → Healthcare Staffing |
| `teaching-jobs.html` | Jobs → Teaching Jobs |
| `contact-us.html` | Contact Us |

The full navigation menu (Home, About Us, Services dropdown, Jobs dropdown,
Contact Us) links between these local files.

## Assets

Each page is the site's **real rendered HTML**, so it looks pixel-identical to
the live site.

### Images

All inline `<img>` images are stored **locally** in the `img/` folder and are
referenced as `img/<filename>`. WordPress size-variants (e.g. `Testi1-300x300.jpg`
in `srcset`) are collapsed to the single base file (`img/Testi1.jpg`).

### CSS / JS / fonts / section backgrounds

These still load from the original `bluediamondmed.com` URLs, so the pages render
correctly in any browser with internet access. Section **background** images are
set inside the site's CSS (not as `<img>` tags), so they currently come from the
live site. The matching image files are already in `img/`; to point the CSS at
them and make the clone **100% self-contained**, run the localizer from any
machine with normal internet access:

```bash
cd bluediamondmed-clone
bash localize.sh
```

It downloads the remaining CSS/JS/font assets and rewrites the references.

## Viewing

Open `index.html` directly in a browser (assets load from the live site), or —
recommended, and required after running `localize.sh` — serve the folder:

```bash
cd bluediamondmed-clone
python3 -m http.server 8000
# visit http://localhost:8000
```
