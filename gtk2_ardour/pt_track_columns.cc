/*
 * Copyright (C) 2026 Ahmed Hadjadj
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

#include <algorithm>
#include <cmath>
#include <cstdio>

#include <ytkmm/menu_elems.h>

#include "pbd/compose.h"
#include "pbd/controllable.h"

#include "ardour/amp.h"
#include "ardour/dB.h"
#include "ardour/gain_control.h"
#include "ardour/internal_send.h"
#include "ardour/plugin_insert.h"
#include "ardour/rc_configuration.h"
#include "ardour/route.h"
#include "ardour/send.h"
#include "ardour/session.h"

#include "gtkmm2ext/menu_elems.h"
#include "gtkmm2ext/utils.h"

#include "ardour_ui.h"
#include "ardour_window.h"
#include "gui_thread.h"
#include "mixer_strip.h"
#include "mixer_ui.h"
#include "panner_ui.h"
#include "plugin_selector.h"
#include "processor_box.h"
#include "pt_track_columns.h"
#include "route_ui.h"
#include "ui_config.h"
#include "widgets/tooltips.h"

#include "pbd/i18n.h"

using namespace ARDOUR;
using namespace ArdourWidgets;
using namespace Gtk;
using namespace Gtk::Menu_Helpers;

#define PX_SCALE(px) std::max ((float)px, rintf ((float)px * UIConfiguration::instance ().get_ui_scale ()))

PTTrackColumns::PTTrackColumns (RouteUI& rui, Session* s)
	: SessionHandlePtr (s)
	, _rui (rui)
	, _inserts_title (_("INSERTS A-E"))
	, _sends_title (_("SENDS A-E"))
	, _io_title (_("I/O"))
	, _input_button (true)
	, _output_button (false)
	, _menu (0)
	, _pan_window (0)
	, _pan_ui (0)
{
	set_spacing (2);

	_inserts_title.set_name ("PTColumnTitle");
	_sends_title.set_name ("PTColumnTitle");
	_io_title.set_name ("PTColumnTitle");

	_inserts_box.set_spacing (1);
	_sends_box.set_spacing (1);
	_io_box.set_spacing (1);

	_inserts_box.pack_start (_inserts_title, false, false);
	_sends_box.pack_start (_sends_title, false, false);
	_io_box.pack_start (_io_title, false, false);

	for (size_t i = 0; i < PTSlotModel::n_slots; ++i) {
		setup_slot (_insert_slots[i], 72);
		_insert_slots[i].signal_button_press_event ().connect (sigc::bind (sigc::mem_fun (*this, &PTTrackColumns::insert_slot_press), i), false);
		_inserts_box.pack_start (_insert_slots[i], false, false);

		setup_slot (_send_slots[i], 72);
		_send_slots[i].signal_button_press_event ().connect (sigc::bind (sigc::mem_fun (*this, &PTTrackColumns::send_slot_press), i), false);
		_sends_box.pack_start (_send_slots[i], false, false);
	}

	_input_button.set_name ("mixer strip button");
	_output_button.set_name ("mixer strip button");
	_input_button.set_size_request (PX_SCALE (84), -1);
	_output_button.set_size_request (PX_SCALE (84), -1);

	_gain_display.set_name ("mixer strip button");
	_gain_display.set_size_request (PX_SCALE (84), -1);
	_gain_display.set_sizing_text ("-inf dB");
	_gain_display.add_events (Gdk::SCROLL_MASK);
	_gain_display.signal_scroll_event ().connect (sigc::mem_fun (*this, &PTTrackColumns::gain_scroll), false);
	set_tooltip (_gain_display, _("Fader gain (scroll to change)"));

	_pan_display.set_name ("mixer strip button");
	_pan_display.set_size_request (PX_SCALE (84), -1);
	_pan_display.signal_button_press_event ().connect (sigc::mem_fun (*this, &PTTrackColumns::pan_press), false);
	set_tooltip (_pan_display, _("Pan (click to open the panner)"));

	_io_box.pack_start (_input_button, false, false);
	_io_box.pack_start (_output_button, false, false);
	_io_box.pack_start (_gain_display, false, false);
	_io_box.pack_start (_pan_display, false, false);

	pack_start (_inserts_box, false, false);
	pack_start (_sends_box, false, false);
	pack_start (_io_box, false, false);

	show_all ();
}

PTTrackColumns::~PTTrackColumns ()
{
	delete _menu;
	delete _pan_window; /* owns _pan_ui */
}

void
PTTrackColumns::setup_slot (ArdourButton& b, int width_px)
{
	b.set_name ("PTSlotButton");
	b.set_elements (ArdourButton::Element (ArdourButton::Edge | ArdourButton::Body | ArdourButton::Text | ArdourButton::Indicator));
	b.set_led_left (true);
	b.set_text_ellipsize (Pango::ELLIPSIZE_END);
	b.set_size_request (PX_SCALE (width_px), PX_SCALE (16));
	b.set_tweaks (ArdourButton::TrackHeader);
}

void
PTTrackColumns::set_route (std::shared_ptr<Route> r)
{
	_route_connections.drop_connections ();
	_route = r;
	if (!_route) {
		return;
	}

	_input_button.set_route (_route, &_rui);
	_output_button.set_route (_route, &_rui);

	/* the master has no sends and no selectable input */
	_sends_box.set_visible (!_route->is_master ());
	_input_button.set_visible (!_route->is_master ());

	_route->processors_changed.connect (_route_connections, invalidator (*this), std::bind (&PTTrackColumns::processors_changed, this, _1), gui_context ());
	_route->gain_control ()->Changed.connect (_route_connections, invalidator (*this), std::bind (&PTTrackColumns::update_gain_display, this), gui_context ());
	if (_route->pan_azimuth_control ()) {
		_route->pan_azimuth_control ()->Changed.connect (_route_connections, invalidator (*this), std::bind (&PTTrackColumns::update_pan_display, this), gui_context ());
	}
	if (_route->pan_width_control ()) {
		_route->pan_width_control ()->Changed.connect (_route_connections, invalidator (*this), std::bind (&PTTrackColumns::update_pan_display, this), gui_context ());
	}

	refresh ();
}

void
PTTrackColumns::processors_changed (RouteProcessorChange c)
{
	if (c.type == RouteProcessorChange::MeterPointChange) {
		return;
	}
	refresh ();
}

void
PTTrackColumns::refresh ()
{
	_processor_connections.drop_connections ();
	_inserts = PTSlotModel::collect_insert_slots (_route);
	_sends   = PTSlotModel::collect_send_slots (_route);

	for (std::vector<PTInsertSlot>::iterator i = _inserts.begin (); i != _inserts.end (); ++i) {
		std::shared_ptr<Processor> p = i->processor.lock ();
		if (p) {
			p->ActiveChanged.connect (_processor_connections, invalidator (*this), std::bind (&PTTrackColumns::refresh, this), gui_context ());
		}
	}
	for (std::vector<PTSendSlot>::iterator i = _sends.begin (); i != _sends.end (); ++i) {
		std::shared_ptr<Send> s = i->send.lock ();
		if (s) {
			s->ActiveChanged.connect (_processor_connections, invalidator (*this), std::bind (&PTTrackColumns::refresh, this), gui_context ());
		}
	}

	update_insert_buttons ();
	update_send_buttons ();
	update_gain_display ();
	update_pan_display ();
}

void
PTTrackColumns::update_insert_buttons ()
{
	for (size_t i = 0; i < PTSlotModel::n_slots; ++i) {
		ArdourButton& b = _insert_slots[i];
		if (i < _inserts.size ()) {
			b.set_text (_inserts[i].label);
			b.set_active_state (_inserts[i].active ? Gtkmm2ext::ExplicitActive : Gtkmm2ext::Off);
			set_tooltip (b, _inserts[i].label);
		} else {
			b.set_text ("");
			b.set_active_state (Gtkmm2ext::Off);
			set_tooltip (b, _("Click to add a plugin"));
		}
	}
	if (_inserts.size () > PTSlotModel::n_slots) {
		set_tooltip (_insert_slots[PTSlotModel::n_slots - 1],
		             string_compose (_("%1 (+%2 more inserts, see the mixer)"),
		                             _inserts[PTSlotModel::n_slots - 1].label,
		                             _inserts.size () - PTSlotModel::n_slots));
	}
}

void
PTTrackColumns::update_send_buttons ()
{
	for (size_t i = 0; i < PTSlotModel::n_slots; ++i) {
		ArdourButton& b = _send_slots[i];
		if (i < _sends.size ()) {
			b.set_text (_sends[i].label);
			b.set_active_state (_sends[i].active ? Gtkmm2ext::ExplicitActive : Gtkmm2ext::Off);
			set_tooltip (b, _sends[i].pre_fader ? string_compose (_("%1 (pre-fader)"), _sends[i].label) : _sends[i].label);
		} else {
			b.set_text ("");
			b.set_active_state (Gtkmm2ext::Off);
			set_tooltip (b, _("Click to add a send"));
		}
	}
}

void
PTTrackColumns::update_gain_display ()
{
	if (!_route) {
		return;
	}
	float db = accurate_coefficient_to_dB (_route->gain_control ()->get_value ());
	if (db < -90.f) {
		_gain_display.set_text (_("-inf"));
	} else {
		char buf[16];
		snprintf (buf, sizeof (buf), "%.1f", db);
		_gain_display.set_text (buf);
	}
}

void
PTTrackColumns::update_pan_display ()
{
	if (!_route || !_route->pan_azimuth_control ()) {
		_pan_display.set_text ("");
		_pan_display.set_sensitive (false);
		return;
	}
	_pan_display.set_sensitive (true);
	_pan_display.set_text (_route->pan_azimuth_control ()->get_user_string ());
}

/* ---- inserts ---- */

bool
PTTrackColumns::insert_slot_press (GdkEventButton* ev, size_t i)
{
	if (ev->type != GDK_BUTTON_PRESS) {
		return true;
	}
	bool filled = i < _inserts.size ();
	if (ev->button == 3) {
		if (filled) {
			popup_insert_menu (i, ev);
		}
		return true;
	}
	if (ev->button == 1) {
		if (filled) {
			open_insert (i);
		} else {
			choose_insert ();
		}
		return true;
	}
	return false;
}

void
PTTrackColumns::open_insert (size_t i)
{
	std::shared_ptr<Processor> p = _inserts[i].processor.lock ();
	if (!p) {
		return;
	}
	MixerStrip* ms = ARDOUR_UI::instance ()->the_mixer ()->pt_strip_by_route (_route);
	if (ms) {
		ms->pt_processor_box ().edit_processor (p);
	}
}

void
PTTrackColumns::choose_insert ()
{
	PluginSelector* ps = ARDOUR_UI::instance ()->the_mixer ()->plugin_selector ();
	ps->set_interested_object (*this);
	ps->show_manager ();
}

bool
PTTrackColumns::use_plugins (const SelectedPlugins& plugins)
{
	if (!_route || !_session) {
		return true;
	}
	for (SelectedPlugins::const_iterator p = plugins.begin (); p != plugins.end (); ++p) {
		std::shared_ptr<Processor> processor (new PluginInsert (*_session, *_route, *p));
		Route::ProcessorStreams     err;
		if (_route->add_processor (processor, PreFader, &err, Config->get_new_plugins_active ()) != 0) {
			return true;
		}
	}
	return false;
}

void
PTTrackColumns::toggle_insert_active (size_t i)
{
	std::shared_ptr<Processor> p = _inserts[i].processor.lock ();
	if (p) {
		p->enable (!p->enabled ());
	}
}

void
PTTrackColumns::remove_insert (size_t i)
{
	std::shared_ptr<Processor> p = _inserts[i].processor.lock ();
	if (p) {
		_route->remove_processor (p);
	}
}

void
PTTrackColumns::popup_insert_menu (size_t i, GdkEventButton* ev)
{
	delete _menu;
	_menu = new Menu;
	MenuList& items = _menu->items ();
	items.push_back (MenuElem (_inserts[i].active ? _("Bypass") : _("Activate"),
	                           sigc::bind (sigc::mem_fun (*this, &PTTrackColumns::toggle_insert_active), i)));
	items.push_back (MenuElem (_("Remove"), sigc::bind (sigc::mem_fun (*this, &PTTrackColumns::remove_insert), i)));
	items.push_back (SeparatorElem ());
	items.push_back (MenuElem (_("Add plugin..."), sigc::mem_fun (*this, &PTTrackColumns::choose_insert)));
	_menu->popup (ev->button, ev->time);
}

/* ---- sends ---- */

bool
PTTrackColumns::send_slot_press (GdkEventButton* ev, size_t i)
{
	if (ev->type != GDK_BUTTON_PRESS) {
		return true;
	}
	bool filled = i < _sends.size ();
	if (ev->button == 3) {
		if (filled) {
			popup_send_menu (i, ev);
		}
		return true;
	}
	if (ev->button == 1) {
		if (filled) {
			open_send (i);
		} else {
			popup_send_target_menu (ev);
		}
		return true;
	}
	return false;
}

void
PTTrackColumns::open_send (size_t i)
{
	std::shared_ptr<Send> s = _sends[i].send.lock ();
	if (!s) {
		return;
	}
	MixerStrip* ms = ARDOUR_UI::instance ()->the_mixer ()->pt_strip_by_route (_route);
	if (ms) {
		/* ProcessorBox opens SendUIWindow for sends */
		ms->pt_processor_box ().edit_processor (s);
	}
}

void
PTTrackColumns::popup_send_target_menu (GdkEventButton* ev)
{
	if (!_session || !_route) {
		return;
	}
	delete _menu;
	_menu = new Menu;
	MenuList& items = _menu->items ();

	std::shared_ptr<RouteList const> routes = _session->get_routes ();
	for (RouteList::const_iterator r = routes->begin (); r != routes->end (); ++r) {
		if ((*r)->is_track () || (*r)->is_master () || (*r)->is_monitor () || (*r)->is_foldbackbus () || *r == _route) {
			continue;
		}
		if (_route->internal_send_for (*r)) {
			continue; /* already sending there */
		}
		items.push_back (Gtkmm2ext::MenuElemNoMnemonic ((*r)->name (), sigc::bind (sigc::mem_fun (*this, &PTTrackColumns::add_send_to), std::weak_ptr<Route> (*r))));
	}
	if (items.empty ()) {
		items.push_back (MenuElem (_("(no bus available)")));
		items.back ().set_sensitive (false);
	}
	_menu->popup (ev->button, ev->time);
}

void
PTTrackColumns::add_send_to (std::weak_ptr<Route> wr)
{
	std::shared_ptr<Route> target = wr.lock ();
	if (!target || !_session || !_route) {
		return;
	}
	/* index -1: append, i.e. post-fader like Pro Tools' default */
	_session->add_internal_send (target, -1, _route);
}

void
PTTrackColumns::remove_send (size_t i)
{
	std::shared_ptr<Send> s = _sends[i].send.lock ();
	if (s) {
		_route->remove_processor (s);
	}
}

void
PTTrackColumns::popup_send_menu (size_t i, GdkEventButton* ev)
{
	delete _menu;
	_menu = new Menu;
	MenuList& items = _menu->items ();
	items.push_back (MenuElem (_("Remove send"), sigc::bind (sigc::mem_fun (*this, &PTTrackColumns::remove_send), i)));
	_menu->popup (ev->button, ev->time);
}

/* ---- I/O ---- */

bool
PTTrackColumns::gain_scroll (GdkEventScroll* ev)
{
	if (!_route) {
		return false;
	}
	float db = accurate_coefficient_to_dB (_route->gain_control ()->get_value ());
	if (ev->direction == GDK_SCROLL_UP) {
		db += 1.f;
	} else if (ev->direction == GDK_SCROLL_DOWN) {
		db -= 1.f;
	} else {
		return false;
	}
	db = std::min (6.f, std::max (-90.f, db));
	_route->gain_control ()->set_value (dB_to_coefficient (db), PBD::Controllable::UseGroup);
	return true;
}

bool
PTTrackColumns::pan_press (GdkEventButton* ev)
{
	if (ev->button != 1 || !_route || !_route->panner_shell ()) {
		return false;
	}
	if (!_pan_window) {
		_pan_window = new ArdourWindow (string_compose (_("Pan: %1"), _route->name ()));
		_pan_ui     = new PannerUI (_session);
		_pan_ui->set_panner (_route->panner_shell (), _route->panner ());
		_pan_window->add (*_pan_ui);
		_pan_ui->show ();
	}
	_pan_window->present ();
	return true;
}
