"""Database triggers enforcing schema invariants."""

from typing import Sequence, Union

from alembic import op

revision: str = "002_triggers"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION forbid_version_update()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'immutable table: updates to % are forbidden', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_passage_versions_immutable
        BEFORE UPDATE ON passage_versions
        FOR EACH ROW EXECUTE FUNCTION forbid_version_update();
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_item_versions_immutable
        BEFORE UPDATE ON item_versions
        FOR EACH ROW EXECUTE FUNCTION forbid_version_update();
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION assign_passage_version_no()
        RETURNS TRIGGER AS $$
        BEGIN
            SELECT COALESCE(MAX(version_no), 0) + 1
              INTO NEW.version_no
              FROM passage_versions
             WHERE passage_id = NEW.passage_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_passage_versions_version_no
        BEFORE INSERT ON passage_versions
        FOR EACH ROW EXECUTE FUNCTION assign_passage_version_no();
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION assign_item_version_no()
        RETURNS TRIGGER AS $$
        BEGIN
            SELECT COALESCE(MAX(version_no), 0) + 1
              INTO NEW.version_no
              FROM item_versions
             WHERE item_id = NEW.item_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_item_versions_version_no
        BEFORE INSERT ON item_versions
        FOR EACH ROW EXECUTE FUNCTION assign_item_version_no();
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION denorm_passage_version_org()
        RETURNS TRIGGER AS $$
        BEGIN
            SELECT organization_id
              INTO NEW.organization_id
              FROM passages
             WHERE id = NEW.passage_id;
            IF NEW.organization_id IS NULL THEN
                RAISE EXCEPTION 'passage % not found for version denorm', NEW.passage_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_passage_versions_org_denorm
        BEFORE INSERT ON passage_versions
        FOR EACH ROW EXECUTE FUNCTION denorm_passage_version_org();
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_item_approval_gate()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.status = 'approved' AND (OLD.status IS DISTINCT FROM 'approved') THEN
                IF NEW.current_version_id IS NULL THEN
                    RAISE EXCEPTION 'cannot approve item without current_version_id';
                END IF;
                IF EXISTS (
                    SELECT 1
                      FROM quality_checks
                     WHERE target_type = 'item_version'
                       AND target_id = NEW.current_version_id
                       AND severity = 'must'
                       AND passed = false
                ) THEN
                    RAISE EXCEPTION 'item blocked by quality gate';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_items_approval_gate
        BEFORE UPDATE OF status ON items
        FOR EACH ROW EXECUTE FUNCTION enforce_item_approval_gate();
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_passage_approval_gate()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.status = 'approved' AND (OLD.status IS DISTINCT FROM 'approved') THEN
                IF NEW.current_version_id IS NULL THEN
                    RAISE EXCEPTION 'cannot approve passage without current_version_id';
                END IF;
                IF EXISTS (
                    SELECT 1
                      FROM quality_checks
                     WHERE target_type = 'passage_version'
                       AND target_id = NEW.current_version_id
                       AND severity = 'must'
                       AND passed = false
                ) THEN
                    RAISE EXCEPTION 'passage blocked by quality gate';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_passages_approval_gate
        BEFORE UPDATE OF status ON passages
        FOR EACH ROW EXECUTE FUNCTION enforce_passage_approval_gate();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_passages_approval_gate ON passages")
    op.execute("DROP TRIGGER IF EXISTS trg_items_approval_gate ON items")
    op.execute("DROP TRIGGER IF EXISTS trg_passage_versions_org_denorm ON passage_versions")
    op.execute("DROP TRIGGER IF EXISTS trg_item_versions_version_no ON item_versions")
    op.execute("DROP TRIGGER IF EXISTS trg_passage_versions_version_no ON passage_versions")
    op.execute("DROP TRIGGER IF EXISTS trg_item_versions_immutable ON item_versions")
    op.execute("DROP TRIGGER IF EXISTS trg_passage_versions_immutable ON passage_versions")
    op.execute("DROP FUNCTION IF EXISTS enforce_passage_approval_gate()")
    op.execute("DROP FUNCTION IF EXISTS enforce_item_approval_gate()")
    op.execute("DROP FUNCTION IF EXISTS denorm_passage_version_org()")
    op.execute("DROP FUNCTION IF EXISTS assign_item_version_no()")
    op.execute("DROP FUNCTION IF EXISTS assign_passage_version_no()")
    op.execute("DROP FUNCTION IF EXISTS forbid_version_update()")
