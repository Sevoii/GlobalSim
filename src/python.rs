use pyo3::prelude::*;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::types::PyBytes;

#[pyclass(unsendable, name = "PreparedRace")]
struct PythonRace {
    race: Option<crate::PreparedRace>,
    metadata: String,
    packet: Vec<u8>,
}

#[pymethods]
impl PythonRace {
    #[new]
    fn new(input: &str) -> PyResult<Self> {
        Ok(Self { race: Some(crate::PreparedRace::new(input).map_err(PyValueError::new_err)?),
            metadata: String::new(), packet: Vec::new() })
    }

    fn prepare(&mut self, input: &str) -> PyResult<()> {
        if self.race.is_none() {
            return Err(PyRuntimeError::new_err("Prepared race has been closed"));
        }
        // Keep the existing preparation if the replacement is invalid.
        self.race = Some(crate::PreparedRace::new(input).map_err(PyValueError::new_err)?);
        Ok(())
    }

    fn run_wire<'py>(&mut self, py: Python<'py>, seed: i64) -> PyResult<Bound<'py, PyBytes>> {
        let race = self.race.as_mut().ok_or_else(|| PyRuntimeError::new_err("Prepared race has been closed"))?;
        let simulation = race.run(seed).map_err(PyValueError::new_err)?;
        simulation.into_binary(&mut self.metadata, &mut self.packet);
        Ok(PyBytes::new(py, &self.packet))
    }

    fn close(&mut self) {
        self.race = None;
        self.metadata = String::new();
        self.packet = Vec::new();
    }
}

#[pymodule]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PythonRace>()
}
