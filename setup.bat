RMDIR /Q/S build
RMDIR /Q/S dist
RMDIR /Q/S wol_api.egg-info
python setup.py sdist bdist_wheel
python -m twine upload dist/* -u __token__ -p %PYPI_TOKEN%