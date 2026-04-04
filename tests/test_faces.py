from unittest import TestCase

from inkypal.faces import IDLE_FACES, list_faces, resolve_face


class FaceTests(TestCase):
    def test_list_faces_is_sorted(self) -> None:
        faces = list_faces()
        self.assertEqual(faces, sorted(faces))

    def test_idle_faces_are_resolvable(self) -> None:
        for face in IDLE_FACES:
            resolved_name, resolved_text = resolve_face(face)
            self.assertEqual(resolved_name, face)
            self.assertTrue(resolved_text)

    def test_resolve_face_defaults_to_happy(self) -> None:
        self.assertEqual(resolve_face(None), ("happy", "(o_o)"))

    def test_resolve_face_rejects_unknown_face(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown face"):
            resolve_face("missing")
