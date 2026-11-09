//! JavaScript bindings (`wasm` feature, wasm32-unknown-unknown) over the
//! prepared-race API. Each instance is confined to the JS realm that made it;
//! for parallel seeds, give every Web Worker its own module and instances.
use wasm_bindgen::prelude::*;

/// Seeds cross the boundary as JS numbers; reject anything that is not an
/// exactly representable integer rather than silently truncating it.
fn seed(value: f64) -> Result<i64, JsError> {
    const MAX_SAFE: f64 = 9_007_199_254_740_991.;
    if value.fract() != 0. || value.abs() > MAX_SAFE {
        return Err(JsError::new("Seed must be a safe integer"));
    }
    Ok(value as i64)
}

fn error(message: String) -> JsError { JsError::new(&message) }

#[wasm_bindgen]
pub struct PreparedRace {
    race: crate::PreparedRace,
    metadata: String,
    packet: Vec<u8>,
}

#[wasm_bindgen]
impl PreparedRace {
    /// Prepare one JSON race request (the same shape as a worker input line).
    #[wasm_bindgen(constructor)]
    pub fn new(input: &str) -> Result<PreparedRace, JsError> {
        Ok(Self { race: crate::PreparedRace::new(input).map_err(error)?,
            metadata: String::new(), packet: Vec::new() })
    }

    /// Replace the preparation. An invalid replacement keeps the existing one.
    pub fn prepare(&mut self, input: &str) -> Result<(), JsError> {
        self.race = crate::PreparedRace::new(input).map_err(error)?;
        Ok(())
    }

    /// One seed as the complete JSON reply, replay frames included.
    #[wasm_bindgen(js_name = runJson)]
    pub fn run_json(&mut self, seed: f64) -> Result<String, JsError> {
        let mut out = String::new();
        self.race.run(self::seed(seed)?).map_err(error)?.write_json(&mut out);
        Ok(out)
    }

    /// One seed as a JSON reply without replay frames or frame metadata;
    /// the fast path for Monte Carlo batches.
    #[wasm_bindgen(js_name = runResults)]
    pub fn run_results(&mut self, seed: f64) -> Result<String, JsError> {
        let value = self.race.run_value(self::seed(seed)?, false).map_err(error)?;
        let mut out = String::new();
        crate::json::to_string_into(&value, &mut out);
        Ok(out)
    }

    /// One seed as a lossless GSIMRP01 packet (see docs/BINARY-REPLAY.md).
    #[wasm_bindgen(js_name = runBinary)]
    pub fn run_binary(&mut self, seed: f64) -> Result<Vec<u8>, JsError> {
        let simulation = self.race.run(self::seed(seed)?).map_err(error)?;
        simulation.into_binary(&mut self.metadata, &mut self.packet);
        Ok(self.packet.clone())
    }
}

/// Register `data/course_geometry/<courseId>.json` (its exact text) before
/// preparing a race that uses world geometry on that course.
#[cfg(feature = "external-geometry")]
#[wasm_bindgen(js_name = registerCourseGeometry)]
pub fn register_course_geometry(course_id: i32, json: String) {
    crate::register_course_geometry(course_id, json);
}
