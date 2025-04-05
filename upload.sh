#!/bin/bash

PKGNAME="meower"
PYPIREPO="pypi"  # change to "testpypi" for testing

rm -rf dist/ build/ ${PKGNAME}.egg-info/ __pycache__/ meow/__pycache__/

pip install --upgrade cython wheel twine setuptools auditwheel patchelf

echo "building with optimizations..."
CFLAGS="-Oz -flto=4 -fno-ident -march=native" \
LDFLAGS="-Wl,--gc-sections -Wl,--build-id=none" \
python setup.py build_ext --inplace

echo "building source distribution..."
python setup.py sdist

echo "building wheel..."
python setup.py bdist_wheel

echo "repairing wheel for PyPI compatibility..."
WHEEL_FILE=$(ls dist/*.whl)
auditwheel repair "$WHEEL_FILE" --plat manylinux2014_aarch64

echo "checking distributions..."
twine check dist/*.tar.gz wheelhouse/*.whl

echo -e "\nuploading to ${PYPIREPO}..."
echo "uploading source distribution..."
twine upload --repository ${PYPIREPO} dist/*.tar.gz

echo "uploading wheel..."
twine upload --repository ${PYPIREPO} wheelhouse/*.whl

echo "upload complete"