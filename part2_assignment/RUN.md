# Run all tests
pytest -q tests/

# Run sample generator and solvers
python gen_factory.py
python factory/main.py < sample_factory_input.json
python gen_belts.py
python belts/main.py < sample_belt_input.json

# Verify results
python verify_factory.py
python verify_belts.py
