# NET coverage

Status: future project. NET is not active in the current branch.

Purpose when implemented: call MESA reaction-network setup, reaction rates, and
one-zone burn helpers from Python.

## Source

```text
$MESA_DIR/net/public/net_lib.f90
```

## Available Now

No Python API and no Fortran wrapper are available yet.

NET is not required for the current static-composition EOS/KAP zone-query path:

```text
composition -> CHEM -> EOS -> KAP
```

## Not Wrapped Yet

```text
net_init
net_shutdown
free_net_handle
net_ptr
net_start_def
net_finish_def
read_net_file
net_add_iso
net_add_isos
net_remove_iso
net_remove_isos
net_add_reaction
net_add_reactions
net_remove_reaction
net_remove_reactions
show_net_reactions
show_net_reactions_and_info
show_net_species
show_net_params
net_set_fe56ec_fake_factor
net_set_logTcut
net_set_eps_nuc_cancel
net_setup_tables
get_chem_id_table
get_chem_id_table_ptr
get_net_iso_table
get_net_iso_table_ptr
get_reaction_id_table
get_reaction_id_table_ptr
get_net_reaction_table
get_net_reaction_table_ptr
net_get
net_get_rates_only
net_get_symbolic_d_dxdt_dx
net_get_with_Qs
net_1_zone_burn
net_1_zone_burn_const_density
net_1_zone_burn_const_P
clean_up_fractions
clean1
```

## Notes

NET should be scoped separately because it needs network definition, reaction
tables, rate controls, and cleanup rules. Do not add NET only to support static
EOS/KAP calls; those already work through CHEM, EOS, and KAP.
