# Local data

No traffic images are included. Generate synthetic input or prepare authorized images.

One resolution:
~~~bash
python scripts/prepare_data.py images --input /path/to/images --out data/prepared/images_01.epraw
~~~

Mixed resolutions:
~~~bash
python scripts/prepare_image_groups.py --input /path/to/images --out data/prepared/groups_01 --limit 6
~~~

Use --limit 0 for all supported files. The group tool preserves native dimensions and writes source hashes. Read groups.json for the selection and generated replay names. Point to each official split separately. Large decoded collections need disk space; an estimate is printed before writing.

Keep images, annotations, replays and captures out of Git.

