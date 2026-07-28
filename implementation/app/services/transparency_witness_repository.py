from app.domain.transparency_witness import TransparencyWitness


class TransparencyWitnessRepository:
    def __init__(self, witnesses=()) -> None:
        self._witnesses: dict[str, TransparencyWitness] = {}
        for witness in witnesses:
            self.add(witness)

    def add(self, witness: TransparencyWitness) -> None:
        if witness.witness_id in self._witnesses:
            raise ValueError("duplicate-transparency-witness")
        self._witnesses[witness.witness_id] = witness

    def get(self, witness_id: str) -> TransparencyWitness:
        try:
            return self._witnesses[witness_id]
        except KeyError as error:
            raise LookupError(f"Unknown transparency witness: {witness_id}") from error

    def list_trusted_witnesses(self) -> list[TransparencyWitness]:
        return list(self._witnesses.values())
